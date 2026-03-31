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

        with open("features/registry/features_v1.json") as f:
            self.feature_cols = json.load(f)

    # -----------------------------------------
    # 构建数据集（🔥修复：强制对齐）
    # -----------------------------------------
    def build_dataset(self, df):

        df = df.copy()

        feature_cols = [
            col for col in self.feature_cols
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col])
        ]

        # 🔥关键：统一drop，确保X和meta完全对齐
        df = df.dropna(subset=feature_cols + ["future_return"])

        X = df[feature_cols]
        y = df["future_return"]

        # 🔥必须带 symbol（否则后面merge全错）
        meta = df[["trade_date", "symbol", "industry", "future_return"]]

        return X, y, meta

    # -----------------------------------------
    # 因子体检
    # -----------------------------------------
    def run_factor_diagnostics(self, df):

        print("\n===== 因子体检开始 =====")

        factor_cols = [
            col for col in self.feature_cols
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col])
        ]

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
    # Walk-Forward
    # -----------------------------------------
    def run_walk_forward(self, start_date, end_date, horizon=1):

        print("===== 加载数据 =====")

        df = self.db.load_features(start_date, end_date)

        if df.empty:
            raise ValueError("feature_values 无数据")

        print("Feature时间范围:", df["trade_date"].min(), "→", df["trade_date"].max())

        # -------------------------------
        # 合并价格
        # -------------------------------
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

        # -------------------------------
        # Label
        # -------------------------------
        df = self.label_engine.add_future_return(df, horizon)

        # ✅ debug
        print("\n===== LABEL检查 =====")
        print(df["future_return"].describe())
        print("NaN比例:", df["future_return"].isna().mean())

        print("\n===== 横截面检查 =====")
        print(df.groupby("trade_date").size().describe())

        # -------------------------------
        self.run_factor_diagnostics(df)

        # -------------------------------
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

            train_df = df[
                (df["trade_date"] >= current_start) &
                (df["trade_date"] < train_end)
            ]

            test_df = df[
                (df["trade_date"] >= train_end) &
                (df["trade_date"] < test_end)
            ]

            if len(train_df) == 0 or len(test_df) == 0:
                current_start += pd.DateOffset(days=test_days)
                continue

            X_train, y_train, _ = self.build_dataset(train_df)
            X_test, y_test, meta_test = self.build_dataset(test_df)

            print("\n===== 对齐检查 =====")
            print("X_test:", X_test.shape)
            print("meta_test:", meta_test.shape)
            print("index一致:", (X_test.index == meta_test.index).all())

            trainer = AlphaTrainer()
            trainer.fit(X_train, y_train)

            result = self.predictor.predict(trainer, X_test, meta_test)
            # ✅ 把 close_adj 从 test_df 合并回 result
            result = result.merge(
                test_df[["trade_date", "symbol", "close_adj"]],
                on=["trade_date", "symbol"],
                how="left"
            )

            # 🔍 debug
            print("\n===== close_adj检查 =====")
            print("NaN比例:", result["close_adj"].isna().mean())            

            # ✅ debug
            print("\n===== Predictor输出 =====")
            print(result.head())
            print("score NaN比例:", result["score"].isna().mean())

            #result = self.predictor.neutralize_by_industry(result)
            #result["score"] = result["score_neutral"]

            print("\n===== FINAL检查 =====")
            print(result[["score", "future_return"]].describe())

            valid_df = result.dropna(subset=["score", "future_return"])
            print("有效样本数:", len(valid_df))
            print("\n===== evaluator输入检查 =====")
            valid_df = result.dropna(subset=["score", "future_return"])
            print("有效样本数:", len(valid_df))

            all_predictions.append(result)

            current_start += pd.DateOffset(days=test_days)

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