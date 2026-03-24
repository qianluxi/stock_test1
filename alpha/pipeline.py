import pandas as pd
import numpy as np
from datetime import datetime

from alpha.label_engine import LabelEngine
from alpha.trainer import AlphaTrainer
from alpha.predictor import AlphaPredictor
from alpha.evaluator import AlphaEvaluator

# 👇 新增
from alpha.factor_diagnostics import FactorDiagnostics

# 👇 独立运行支持
from db.database import SQLiteDB
from factors.indicator_engine import IndicatorEngine


class AlphaPipeline:

    def __init__(self, db, feature_builder):

        self.db = db
        self.feature_builder = feature_builder

        self.label_engine = LabelEngine()
        self.trainer = AlphaTrainer()
        self.predictor = AlphaPredictor()
        self.evaluator = AlphaEvaluator()

        # 🔥 新增
        self.diagnostics = FactorDiagnostics()

    # -----------------------------------------
    # 构建数据集
    # -----------------------------------------
    def build_dataset(self, df):

        df = df.copy()

        feature_cols = [
            col for col in df.columns
            if col not in [
                "trade_date",
                "symbol",
                "future_return",
                "industry"
            ]
        ]

        df = df.dropna(subset=feature_cols + ["future_return"])

        X = df[feature_cols]
        y = df["future_return"]
        meta = df[["trade_date", "symbol", "future_return"]]

        return X, y, meta

    # -----------------------------------------
    # 🔥 因子体检（新增）
    # -----------------------------------------
    def run_factor_diagnostics(self, df):

        print("\n===== 因子体检开始 =====")

        factor_cols = [
            col for col in df.columns
            if col not in [
                "trade_date",
                "symbol",
                "future_return",
                "industry"
            ]
        ]

        # 只保留数值型（防止 LightGBM 报错）
        factor_cols = [
            col for col in factor_cols
            if pd.api.types.is_numeric_dtype(df[col])
        ]

        # -------------------------------
        # 1️⃣ IC
        # -------------------------------
        ic = self.diagnostics.calc_factor_ic(df, factor_cols)
        print("\n===== 因子IC Top10 =====")
        print(ic.head(10))

        # -------------------------------
        # 2️⃣ IC_IR
        # -------------------------------
        ic_ir = self.diagnostics.calc_ic_ir(df, factor_cols)
        print("\n===== IC_IR Top10 =====")
        print(ic_ir.head(10))

        # -------------------------------
        # 3️⃣ 分布
        # -------------------------------
        stats = self.diagnostics.factor_stats(df, factor_cols)
        print("\n===== 因子分布（低波动Top10）=====")
        print(stats.head(10))

        # -------------------------------
        # 4️⃣ 高相关因子提示（简化版）
        # -------------------------------
        corr = self.diagnostics.factor_corr(df, factor_cols)

        print("\n===== 高相关因子（>0.9）=====")
        high_corr_pairs = []

        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                val = corr.iloc[i, j]
                if abs(val) > 0.9:
                    high_corr_pairs.append(
                        (corr.columns[i], corr.columns[j], val)
                    )

        for p in high_corr_pairs[:10]:
            print(p)

        print("\n===== 因子体检结束 =====")

    # -----------------------------------------
    # Walk-Forward 主逻辑
    # -----------------------------------------
    def run_walk_forward(
        self,
        start_date,
        end_date,
        horizon=5,
        train_years=5,
        test_years=1
    ):

        print("===== 加载数据 =====")

        df = self.db.load_data(start_date, end_date)

        df["trade_date"] = pd.to_datetime(df["trade_date"])

        df = self.feature_builder(df)
        df = self.label_engine.add_future_return(df, horizon)

        df = df.sort_values("trade_date")

        # 🔥 👉 在这里执行因子体检（只跑一次）
        self.run_factor_diagnostics(df)

        all_predictions = []

        unique_dates = sorted(df["trade_date"].unique())

        start_dt = pd.to_datetime(unique_dates[0])
        end_dt = pd.to_datetime(unique_dates[-1])

        current_start = start_dt

        while True:

            train_end = current_start + pd.DateOffset(years=train_years)
            test_end = train_end + pd.DateOffset(years=test_years)

            if test_end > end_dt:
                break

            print(f"\n===== 窗口: {current_start.date()} → {test_end.date()} =====")

            train_df = df[
                (df["trade_date"] >= current_start) &
                (df["trade_date"] < train_end)
            ]

            test_df = df[
                (df["trade_date"] >= train_end) &
                (df["trade_date"] < test_end)
            ]

            if len(train_df) == 0 or len(test_df) == 0:
                break

            X_train, y_train, _ = self.build_dataset(train_df)
            X_test, y_test, meta_test = self.build_dataset(test_df)

            trainer = AlphaTrainer()
            trainer.fit(X_train, y_train)

            result = self.predictor.predict(
                trainer,
                X_test,
                meta_test
            )

            # 行业信息
            result = result.merge(
                test_df[["trade_date", "symbol", "industry"]],
                on=["trade_date", "symbol"],
                how="left"
            )

            # 行业中性化
            result = self.predictor.neutralize_by_industry(result)
            result["score"] = result["score_neutral"]

            # 合并价格
            result = result.merge(
                test_df[["trade_date", "symbol", "close_adj"]],
                on=["trade_date", "symbol"],
                how="left"
            )

            all_predictions.append(result)

            current_start = current_start + pd.DateOffset(years=test_years)

        if not all_predictions:
            raise ValueError("Walk-forward 无有效窗口")

        final_result = pd.concat(all_predictions)
        final_result = final_result.sort_values("trade_date")

        # -----------------------------------------
        # 行业中性化验证
        # -----------------------------------------
        print("\n===== 行业中性化验证 =====")
        industry_score_mean = final_result.groupby(
            ["trade_date", "industry"]
        )["score"].mean()

        print(industry_score_mean.head(20))

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


# =========================================
# 独立运行
# =========================================
if __name__ == "__main__":

    print("===== Alpha Pipeline 启动 =====")

    db = SQLiteDB("db/stock.db")
    db.connect()

    engine = IndicatorEngine()

    def feature_builder(df):
        return engine.compute_all(df)

    pipeline = AlphaPipeline(db, feature_builder)

    report, result, curve = pipeline.run_walk_forward(
        start_date="2018-01-01",
        end_date="2025-01-01"
    )

    print("\n===== 结果 =====")
    print(report)

    db.close()