import pandas as pd
import numpy as np
from datetime import datetime

from alpha.label_engine import LabelEngine
from alpha.trainer import AlphaTrainer
from alpha.predictor import AlphaPredictor
from alpha.evaluator import AlphaEvaluator

# 👇 新增（用于独立运行）
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

    # -----------------------------------------
    # 构建数据集
    # -----------------------------------------
    def build_dataset(self, df):

        df = df.copy()

        feature_cols = [
            col for col in df.columns
            if col not in ["trade_date", "symbol", "future_return"]
        ]

        # ✅ 去NaN（关键）
        df = df.dropna(subset=feature_cols + ["future_return"])

        X = df[feature_cols]
        y = df["future_return"]
        meta = df[["trade_date", "symbol", "future_return"]]

        return X, y, meta

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

        # ✅ 时间统一
        df["trade_date"] = pd.to_datetime(df["trade_date"])

        df = self.feature_builder(df)
        df = self.label_engine.add_future_return(df, horizon)

        df = df.sort_values("trade_date")

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

            # ✅ 修复 datetime 比较（核心）
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

            # ✅ 改为传 trainer（关键）
            result = self.predictor.predict(
                trainer,
                X_test,
                meta_test
            )

            # ✅ 合并 close_adj（用于收益计算）
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

        print("\n===== 统一评估 =====")

        ic = self.evaluator.calc_daily_ic(final_result)
        rank_ic = self.evaluator.calc_rank_ic(final_result)
        quantile = self.evaluator.quantile_return(final_result)

        # 🔥 新增：收益曲线
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
# 🔥 让模块可以独立运行
# =========================================
if __name__ == "__main__":

    print("===== Alpha Pipeline 启动 =====")

    db = SQLiteDB("db/stock.db")
    db.connect()

    # ✅ 使用你已有的因子引擎
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