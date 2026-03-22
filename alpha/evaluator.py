import numpy as np
import pandas as pd


class AlphaEvaluator:

    # -----------------------------------
    # IC（信息系数）
    # -----------------------------------
    def calc_daily_ic(self, df: pd.DataFrame):

        ic_list = []

        for date, group in df.groupby("trade_date"):

            group = group.dropna(subset=["score", "future_return"])

            if len(group) < 5:
                continue

            if group["score"].std() == 0:
                continue

            ic = group["score"].corr(group["future_return"])
            ic_list.append(ic)

        return np.nanmean(ic_list)

    # -----------------------------------
    # Rank IC（排序相关）
    # -----------------------------------
    def calc_rank_ic(self, df: pd.DataFrame):

        ic_list = []

        for date, group in df.groupby("trade_date"):

            group = group.dropna(subset=["score", "future_return"])

            if len(group) < 5:
                continue

            if group["score"].std() == 0:
                continue

            ic = group["score"].rank().corr(
                group["future_return"].rank()
            )

            ic_list.append(ic)

        return np.nanmean(ic_list)

    # -----------------------------------
    # 分组收益（更稳版本）
    # -----------------------------------
    def quantile_return(self, df: pd.DataFrame, q: int = 5):

        df = df.copy()

        def safe_qcut(x):
            try:
                return pd.qcut(x, q, labels=False, duplicates="drop")
            except:
                return pd.Series([np.nan] * len(x), index=x.index)

        df["quantile"] = df.groupby("trade_date")["score"].transform(safe_qcut)

        # 每日收益
        daily = df.groupby(["trade_date", "quantile"])["future_return"].mean().unstack()

        if daily.empty or daily.shape[1] < 2:
            return {
                "top_mean": np.nan,
                "bottom_mean": np.nan
            }

        top = daily.iloc[:, -1]
        bottom = daily.iloc[:, 0]

        return {
            "top_mean": top.mean(),
            "bottom_mean": bottom.mean(),
        }

    # -----------------------------------
    # 🔥 新增：多空收益曲线（核心）
    # -----------------------------------
    def long_short_curve(self, df: pd.DataFrame, top_k: int = 20):

        df = df.copy()

        df = df.sort_values(["symbol", "trade_date"])

        # 横截面排名
        df["rank"] = df.groupby("trade_date")["score"] \
            .rank(ascending=False, method="first")

        # 多空标记
        df["long"] = (df["rank"] <= top_k).astype(int)
        df["short"] = (df["rank"] > (
            df.groupby("trade_date")["rank"].transform("max") - top_k
        )).astype(int)

        # 实际收益（下一期）
        horizon = 5

        df["ret"] = (
            df.groupby("symbol")["close_adj"]
            .shift(-horizon) / df["close_adj"] - 1
        )

        # 只做多，不做空
        df["ls_ret"] = df["long"].shift(1) * df["ret"]

        daily = df.groupby("trade_date")["ls_ret"].mean()

        curve = (1 + daily.fillna(0)).cumprod()

        return curve

    # -----------------------------------
    # 🔥 新增：绩效指标
    # -----------------------------------
    def performance(self, curve: pd.Series):

        ret = curve.pct_change().dropna()

        if len(ret) == 0:
            return {}

        sharpe = ret.mean() / ret.std() * np.sqrt(252)

        max_dd = (curve / curve.cummax() - 1).min()

        total_ret = curve.iloc[-1]

        return {
            "TotalReturn": total_ret,
            "Sharpe": sharpe,
            "MaxDrawdown": max_dd
        }