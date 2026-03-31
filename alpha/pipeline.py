import pandas as pd
import numpy as np
import json

from alpha.label_engine import LabelEngine
from alpha.trainer import AlphaTrainer
from alpha.predictor import AlphaPredictor
from alpha.evaluator import AlphaEvaluator
from alpha.factor_diagnostics import FactorDiagnostics

from db.database import SQLiteDB


class AlphaPipeline:

    def __init__(self, db):
        self.db = db
        self.label_engine = LabelEngine()
        self.trainer = AlphaTrainer()
        self.predictor = AlphaPredictor()
        self.evaluator = AlphaEvaluator()
        self.diagnostics = FactorDiagnostics()

        # 加载所有候选特征（原始特征列表）
        with open("features/registry/features_v1.json") as f:
            self.all_feature_cols = json.load(f)

    # -----------------------------------------
    # 特征筛选（基于训练集）
    # -----------------------------------------
    def select_features(self, train_df, feature_candidates):
        """
        对训练集进行特征筛选：
        1. 剔除 IC 绝对值 <= 0.02 的特征
        2. 剔除高相关（>0.9）的冗余特征
        """
        if len(train_df) == 0:
            return []

        # 计算 IC
        ic = self.diagnostics.calc_factor_ic(train_df, feature_candidates)
        # 保留 |IC| > 0.02 的特征
        selected = ic[ic.abs() > 0.005].index.tolist()
        if not selected:
            return []

        # 计算相关性矩阵
        corr = train_df[selected].corr().abs()
        to_drop = set()
        for i in range(len(corr.columns)):
            for j in range(i):
                if corr.iloc[i, j] > 0.95:
                    # 保留 IC 绝对值更大的那个
                    col_i = corr.columns[i]
                    col_j = corr.columns[j]
                    ic_i = abs(ic.loc[col_i])
                    ic_j = abs(ic.loc[col_j])
                    if ic_i >= ic_j:
                        to_drop.add(col_j)
                    else:
                        to_drop.add(col_i)

        final_features = [c for c in selected if c not in to_drop]
        print(f"[特征筛选] 候选 {len(feature_candidates)} → {len(selected)} (IC>0.02) → {len(final_features)} (去冗余)")
        return final_features

    # -----------------------------------------
    # 构建数据集（动态特征）
    # -----------------------------------------
    def build_dataset(self, df, feature_cols):
        df = df.copy()
        # 只保留存在的数值特征
        valid_features = [col for col in feature_cols if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
        if not valid_features:
            return pd.DataFrame(), pd.Series(dtype=float), pd.DataFrame()

        # 剔除特征或标签缺失的行
        df = df.dropna(subset=valid_features + ["future_return"])
        X = df[valid_features]
        y = df["future_return"]
        meta = df[["trade_date", "symbol", "industry", "future_return"]]
        return X, y, meta

    # -----------------------------------------
    # 因子体检（保持不变）
    # -----------------------------------------
    def run_factor_diagnostics(self, df):
        print("\n===== 因子体检开始 =====")
        factor_cols = [col for col in self.all_feature_cols if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
        ic = self.diagnostics.calc_factor_ic(df, factor_cols)
        print("\n===== 因子IC Top10 =====")
        print(ic.head(10))

        ic_ir = self.diagnostics.calc_ic_ir(df, factor_cols)
        print("\n===== IC_IR Top10 =====")
        print(ic_ir.head(10))

        stats = self.diagnostics.factor_stats(df, factor_cols)
        print("\n===== 因子分布（低波动Top10）=====")
        print(stats.head(10))

        corr = self.diagnostics.factor_corr(df, factor_cols)
        print("\n===== 高相关因子（>0.9）=====")
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                val = corr.iloc[i, j]
                if abs(val) > 0.9:
                    print(corr.columns[i], corr.columns[j], val)
        print("\n===== 因子体检结束 =====")

    # -----------------------------------------
    # Walk-Forward 主流程
    # -----------------------------------------
    def run_walk_forward(self, start_date, end_date, horizon=1):
        print("===== 加载数据 =====")
        df = self.db.load_features(start_date, end_date)
        if df.empty:
            raise ValueError("feature_values 无数据")
        print("Feature时间范围:", df["trade_date"].min(), "→", df["trade_date"].max())

        # 合并价格和行业
        price_df = self.db.load_prices(start_date, end_date)
        df = df.merge(
            price_df[["trade_date", "symbol", "close_adj"]],
            on=["trade_date", "symbol"],
            how="left"
        )
        industry_df = self.db.load_industry()
        df = df.merge(
            industry_df[["symbol", "industry"]],
            on="symbol",
            how="left"
        )

        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values(["symbol", "trade_date"])

        # 生成标签
        df = self.label_engine.add_future_return(df, horizon)
        print("\n===== LABEL检查 =====")
        print(df["future_return"].describe())
        print("NaN比例:", df["future_return"].isna().mean())
        print("\n===== 横截面检查 =====")
        print(df.groupby("trade_date").size().describe())

        # 因子体检（整体）
        self.run_factor_diagnostics(df)

        # Walk-forward 参数
        train_days = 504
        test_days = 126
        all_predictions = []
        unique_dates = sorted(df["trade_date"].unique())
        current_start = unique_dates[0]
        end_dt = unique_dates[-1]

        while True:
            train_end = current_start + pd.DateOffset(days=train_days)
            test_end = train_end + pd.DateOffset(days=test_days)
            if test_end > end_dt:
                break

            print(f"\n===== 窗口: {current_start.date()} → {test_end.date()} =====")

            train_df = df[(df["trade_date"] >= current_start) & (df["trade_date"] < train_end)]
            test_df = df[(df["trade_date"] >= train_end) & (df["trade_date"] < test_end)]

            if len(train_df) == 0 or len(test_df) == 0:
                current_start += pd.DateOffset(days=test_days)
                continue

            # ---------- 关键步骤：动态特征筛选 ----------
            feature_candidates = [col for col in self.all_feature_cols if col in train_df.columns]
            selected_features = self.select_features(train_df, feature_candidates)
            if not selected_features:
                print("⚠️ 无有效特征，跳过本窗口")
                current_start += pd.DateOffset(days=test_days)
                continue

            # 构建训练集和测试集
            X_train, y_train, _ = self.build_dataset(train_df, selected_features)
            X_test, y_test, meta_test = self.build_dataset(test_df, selected_features)

            if X_train.empty or X_test.empty:
                print("⚠️ 数据为空，跳过")
                current_start += pd.DateOffset(days=test_days)
                continue

            print("训练集特征数:", X_train.shape[1])

            # ---------- 调试：对齐检查 ----------
            print("\n===== 对齐检查 =====")
            print("X_test:", X_test.shape)
            print("meta_test:", meta_test.shape)
            print("index一致:", (X_test.index == meta_test.index).all())

            # 训练模型
            trainer = AlphaTrainer()
            trainer.fit(X_train, y_train)

            # 预测
            result = self.predictor.predict(trainer, X_test, meta_test)

            # ---------- 调试：Predictor 输出 ----------
            print("\n===== Predictor输出 =====")
            print(result.head())
            print("score NaN比例:", result["score"].isna().mean())

            # 合并 close_adj
            result = result.merge(
                test_df[["trade_date", "symbol", "close_adj"]],
                on=["trade_date", "symbol"],
                how="left"
            )

            # ---------- 调试：close_adj 检查 ----------
            print("\n===== close_adj检查 =====")
            print("NaN比例:", result["close_adj"].isna().mean())

            # 可选：行业中性化（当前注释）
            # result = self.predictor.neutralize_by_industry(result)
            # result["score"] = result["score_neutral"]

            # ---------- 调试：FINAL 检查 ----------
            print("\n===== FINAL检查 =====")
            print(result[["score", "future_return"]].describe())

            valid_df = result.dropna(subset=["score", "future_return"])
            print("\n===== evaluator输入检查 =====")
            print("有效样本数:", len(valid_df))

            all_predictions.append(result)

            current_start += pd.DateOffset(days=test_days)

        if not all_predictions:
            print("无任何有效预测，退出")
            return None, None, None

        final_result = pd.concat(all_predictions)

        print("\n===== 统一评估 =====")
        ic = self.evaluator.calc_daily_ic(final_result)
        rank_ic = self.evaluator.calc_rank_ic(final_result)
        quantile = self.evaluator.quantile_return(final_result)
        curve = self.evaluator.long_short_curve(final_result)
        perf = self.evaluator.performance(curve)

        report = {
            "IC": ic,
            "RankIC": rank_ic,
            "TopMean": quantile["top_mean"],
            "BottomMean": quantile["bottom_mean"],
            "LongShortSpread": quantile["top_mean"] - quantile["bottom_mean"],
            **perf
        }
        return report, final_result, curve


if __name__ == "__main__":
    print("===== Alpha Pipeline 启动 =====")
    db = SQLiteDB("db/stock.db")
    db.connect()
    pipeline = AlphaPipeline(db)
    report, result, curve = pipeline.run_walk_forward(
        start_date="2020-01-01",
        end_date="2026-01-01"
    )
    print("\n===== 结果 =====")
    print(report)
    db.close()