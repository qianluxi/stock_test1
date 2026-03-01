# signals/cross_section.py

import pandas as pd
import numpy as np


# =============================
# 必要字段
# =============================

BASE_REQUIRED_COLUMNS = [
    "trade_date",
    "symbol",
    "score",
    "label"
]


# =============================
# 校验函数
# =============================

def validate_cross_section_df(
    df: pd.DataFrame,
    use_mkt_cap: bool = False
):
    """
    校验横截面输入数据
    """
    required = BASE_REQUIRED_COLUMNS.copy()

    if use_mkt_cap:
        required.append("market_cap")

    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"缺少必要字段: {missing}")

    if df.empty:
        raise ValueError("横截面数据为空")

    if df["trade_date"].isna().any():
        raise ValueError("trade_date 存在空值")

    if df["symbol"].isna().any():
        raise ValueError("symbol 存在空值")

    if use_mkt_cap and df["market_cap"].isna().any():
        raise ValueError("market_cap 存在空值")


# =============================
# 主类
# =============================

class CrossSection:

    def __init__(
        self,
        n_groups: int = 5,
        use_mkt_cap_weight: bool = False
    ):
        """
        :param n_groups: 横截面分组数
        :param use_mkt_cap_weight: 是否启用市值加权排名
        """
        self.n_groups = n_groups
        self.use_mkt_cap_weight = use_mkt_cap_weight

    # ---------------------------------
    # 构建基础横截面结构
    # ---------------------------------

    def build_cross_section_df(
        self,
        df_with_score: pd.DataFrame
    ) -> pd.DataFrame:
        """
        构建标准横截面 DataFrame

        输出字段：
            trade_date | symbol | score | label | (market_cap)
        """
        validate_cross_section_df(
            df_with_score,
            use_mkt_cap=self.use_mkt_cap_weight
        )

        cols = BASE_REQUIRED_COLUMNS.copy()

        if self.use_mkt_cap_weight:
            cols.append("market_cap")

        df_cs = (
            df_with_score
            .loc[:, cols]
            .copy()
            .sort_values(["trade_date", "score"], ascending=[True, False])
            .reset_index(drop=True)
        )

        return df_cs

    # ---------------------------------
    # 排名 + 分组
    # ---------------------------------

    def rank_and_group(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        对每个交易日进行：
        1. score 排名
        2. quantile 分组

        返回：
            trade_date | symbol | score | rank | group
        """

        validate_cross_section_df(
            df,
            use_mkt_cap=self.use_mkt_cap_weight
        )

        df = df.copy()

        # ===== 普通排名 =====
        if not self.use_mkt_cap_weight:

            df["rank"] = (
                df.groupby("trade_date")["score"]
                .rank(method="first", ascending=False)
            )

        # ===== 市值加权排名 =====
        else:
            df["rank"] = (
                df.groupby("trade_date")
                .apply(self._weighted_rank)
                .reset_index(level=0, drop=True)
            )

        # ===== 分组（按 rank 等分）=====
        df["group"] = (
            df.groupby("trade_date")["rank"]
            .transform(self._assign_group)
            .astype(int)
        )

        return df

    # ---------------------------------
    # Top / Bottom 提取
    # ---------------------------------

    def top_bottom_filter(
        self,
        df: pd.DataFrame,
        top_n: int = 1,
        bottom_n: int = 1
    ):
        """
        提取每日最高组与最低组
        """

        top = df[df["group"] <= top_n].copy()
        bottom = df[df["group"] >= self.n_groups - bottom_n + 1].copy()

        return top, bottom

    # =================================
    # 内部方法
    # =================================

    def _assign_group(self, ranks: pd.Series):
        """
        根据 rank 分成 n_groups 组
        """
        try:
            return pd.qcut(
                ranks,
                q=self.n_groups,
                labels=range(1, self.n_groups + 1)
            )
        except ValueError:
            # 股票数量太少时退化为等宽切分
            return pd.cut(
                ranks,
                bins=self.n_groups,
                labels=range(1, self.n_groups + 1)
            )

    def _weighted_rank(self, df_day: pd.DataFrame):
        """
        市值加权排名逻辑：
        score * log(market_cap) 作为排序权重
        """

        # 防止极端值
        weight = np.log(df_day["market_cap"].clip(lower=1))

        weighted_score = df_day["score"] * weight

        return weighted_score.rank(method="first", ascending=False)
