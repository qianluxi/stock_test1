import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta


class WalkForwardEngine:

    def __init__(self, pipeline):
        self.pipeline = pipeline

    def run(
        self,
        start_date,
        end_date,
        train_years=5,
        test_years=1,
        horizon=5
    ):

        df = self.pipeline.db.load_data(start_date, end_date)
        df = self.pipeline.feature_builder(df)
        df = self.pipeline.label_engine.add_future_return(df, horizon)
        df = df.dropna(subset=["future_return"])

        df["trade_date"] = pd.to_datetime(df["trade_date"])

        all_predictions = []

        current_start = df["trade_date"].min()
        final_end = df["trade_date"].max()

        while True:

            train_end = current_start + relativedelta(years=train_years)
            test_end = train_end + relativedelta(years=test_years)

            if test_end > final_end:
                break

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

            # 构建数据
            X_train, y_train, _ = self.pipeline.build_dataset(train_df)
            X_test, y_test, meta_test = self.pipeline.build_dataset(test_df)

            # 训练
            self.pipeline.trainer.fit(X_train, y_train)

            # 预测
            result = self.pipeline.predictor.predict(
                self.pipeline.trainer.model,
                X_test,
                meta_test
            )

            all_predictions.append(result)

            print(f"✔ 完成窗口: {current_start.date()} → {test_end.date()}")

            # 滚动
            current_start = current_start + relativedelta(years=test_years)

        final_df = pd.concat(all_predictions).reset_index(drop=True)

        # 统一评估
        ic = self.pipeline.evaluator.calc_daily_ic(final_df)
        rank_ic = self.pipeline.evaluator.calc_rank_ic(final_df)
        quantile = self.pipeline.evaluator.quantile_return(final_df)

        report = {
            "IC": ic,
            "RankIC": rank_ic,
            "TopMean": quantile["top_mean"],
            "BottomMean": quantile["bottom_mean"]
        }

        return report, final_df