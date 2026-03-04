import numpy as np
import pandas as pd


class AlphaEvaluator:

    # -------- IC --------
    def calc_daily_ic(self, df: pd.DataFrame):

        ic_list = []

        for date, group in df.groupby("trade_date"):
            if group["score"].std() == 0:
                continue
            ic = group["score"].corr(group["future_return"])
            ic_list.append(ic)

        return np.nanmean(ic_list)

    # -------- Rank IC --------
    def calc_rank_ic(self, df: pd.DataFrame):

        ic_list = []

        for date, group in df.groupby("trade_date"):
            if group["score"].std() == 0:
                continue
            ic = group["score"].rank().corr(
                group["future_return"].rank()
            )
            ic_list.append(ic)

        return np.nanmean(ic_list)

    # -------- 分组收益 --------
    def quantile_return(self, df: pd.DataFrame, q: int = 5):

        df = df.copy()

        df["quantile"] = df.groupby("trade_date")["score"] \
            .transform(lambda x: pd.qcut(x, q, labels=False, duplicates="drop"))

        top = df[df["quantile"] == q - 1]
        bottom = df[df["quantile"] == 0]

        return {
            "top_mean": top["future_return"].mean(),
            "bottom_mean": bottom["future_return"].mean(),
        }