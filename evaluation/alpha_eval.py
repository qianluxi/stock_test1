# evaluation/alpha_eval.py

import numpy as np
import pandas as pd


TRADING_DAYS = 252


class AlphaEvaluator:

    def __init__(self, df_cs: pd.DataFrame, n_groups: int = 5):
        """
        df_cs 必须包含:
            trade_date | symbol | score | rank | group | ret_1
        """
        self.df = df_cs.copy()
        self.n_groups = n_groups

        self._validate()
        self._prepare_forward_return()

    # ==========================================================
    # 基础校验
    # ==========================================================

    def _validate(self):
        required_cols = [
            "trade_date",
            "symbol",
            "score",
            "group",
            "ret_1"
        ]

        missing = set(required_cols) - set(self.df.columns)
        if missing:
            raise ValueError(f"缺少字段: {missing}")

        if self.df.empty:
            raise ValueError("输入数据为空")

    # ==========================================================
    # 构造未来收益（避免未来函数）
    # ==========================================================

    def _prepare_forward_return(self):
        """
        构造 next-day return
        """
        self.df = self.df.sort_values(["symbol", "trade_date"])

        self.df["fwd_ret"] = (
            self.df
            .groupby("symbol")["ret_1"]
            .shift(-1)
        )

        # 删除最后一天（没有未来收益）
        self.df = self.df.dropna(subset=["fwd_ret"])

    # ==========================================================
    # 分组收益
    # ==========================================================

    def calc_group_return(self):
        """
        计算每日分组收益
        """
        group_ret = (
            self.df
            .groupby(["trade_date", "group"])["fwd_ret"]
            .mean()
            .unstack()
            .sort_index()
        )

        return group_ret

    # ==========================================================
    # 多空组合收益
    # ==========================================================

    def calc_long_short(self):
        group_ret = self.calc_group_return()

        long_ret = group_ret[1]
        short_ret = group_ret[self.n_groups]

        ls_ret = long_ret - short_ret

        result = pd.DataFrame({
            "long": long_ret,
            "short": short_ret,
            "long_short": ls_ret
        })

        return result

    # ==========================================================
    # IC / RankIC
    # ==========================================================

    def calc_ic(self):

        ic = (
            self.df
            .groupby("trade_date", group_keys=False)[["score", "fwd_ret"]]
            .apply(lambda x: x["score"].corr(x["fwd_ret"]))
        )

        rank_ic = (
            self.df
            .groupby("trade_date", group_keys=False)[["score", "fwd_ret"]]
            .apply(lambda x: x["score"].corr(x["fwd_ret"], method="spearman"))
        )

        return pd.DataFrame({
            "IC": ic,
            "RankIC": rank_ic
        })

    # ==========================================================
    # 绩效指标
    # ==========================================================

    @staticmethod
    def _annual_return(daily_ret):
        return (1 + daily_ret.mean()) ** TRADING_DAYS - 1

    @staticmethod
    def _sharpe(daily_ret):
        return daily_ret.mean() / daily_ret.std() * np.sqrt(TRADING_DAYS)

    @staticmethod
    def _max_drawdown(cum_ret):
        rolling_max = cum_ret.cummax()
        drawdown = cum_ret / rolling_max - 1
        return drawdown.min()

    # ==========================================================
    # 汇总报告
    # ==========================================================

    def performance_report(self):

        ls_df = self.calc_long_short()
        ic_df = self.calc_ic()

        # 累计收益
        cum_ls = (1 + ls_df["long_short"]).cumprod()

        report = {
            "Annual Return (LS)": self._annual_return(ls_df["long_short"]),
            "Sharpe (LS)": self._sharpe(ls_df["long_short"]),
            "Max Drawdown (LS)": self._max_drawdown(cum_ls),

            "IC Mean": ic_df["IC"].mean(),
            "IC Std": ic_df["IC"].std(),
            "ICIR": ic_df["IC"].mean() / ic_df["IC"].std(),

            "RankIC Mean": ic_df["RankIC"].mean(),
        }

        return report
