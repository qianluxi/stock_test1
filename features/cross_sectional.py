import pandas as pd
import numpy as np


# =========================
# Rank（全市场）
# =========================
def add_rank(df, cols):

    df = df.copy()

    for col in cols:

        df[f"{col}_rank"] = df.groupby("trade_date")[col].rank(
            pct=True,
            method="average"
        )

    return df


# =========================
# Rank（行业内）
# =========================
def add_rank_industry(df, cols):

    df = df.copy()

    for col in cols:

        df[f"{col}_rank_ind"] = df.groupby(
            ["trade_date", "industry"]
        )[col].rank(
            pct=True,
            method="average"
        )

    return df


# =========================
# 双排序（可选增强）
# =========================
def add_rank_both(df, cols):

    df = df.copy()

    df = add_rank(df, cols)
    df = add_rank_industry(df, cols)

    return df


# =========================
# 分位数分桶（可用于分析）
# =========================
def add_quantile_bucket(df, col, q=5):

    df = df.copy()

    df[f"{col}_bucket"] = df.groupby("trade_date")[col].transform(
        lambda x: pd.qcut(
            x.rank(method="first"),
            q,
            labels=False,
            duplicates="drop"
        )
    )

    return df


# =========================
# 横截面归一化（0~1）
# =========================
def normalize_cross_section(df, cols):

    df = df.copy()

    for col in cols:

        df[f"{col}_norm"] = df.groupby("trade_date")[col].transform(
            lambda x: _minmax(x)
        )

    return df


def _minmax(x):

    min_val = x.min()
    max_val = x.max()

    if max_val - min_val == 0:
        return pd.Series(np.zeros(len(x)), index=x.index)

    return (x - min_val) / (max_val - min_val + 1e-8)