import pandas as pd
import numpy as np


# =========================
# Winsorize（横截面去极值）
# =========================
def winsorize(df, cols, lower=0.01, upper=0.99):

    df = df.copy()

    for col in cols:

        df[col] = df.groupby("trade_date")[col].transform(
            lambda x: _clip_series(x, lower, upper)
        )

    return df


def _clip_series(x, lower, upper):

    if x.isna().all():
        return x

    low = x.quantile(lower)
    high = x.quantile(upper)

    return x.clip(lower=low, upper=high)


# =========================
# Z-Score（横截面标准化）
# =========================
def zscore(df, cols):

    df = df.copy()

    for col in cols:

        df[f"{col}_z"] = df.groupby("trade_date")[col].transform(
            lambda x: _zscore_series(x)
        )

    return df


def zscore_industry(df, cols):

    df = df.copy()

    for col in cols:

        df[f"{col}_z_ind"] = df.groupby(
            ["trade_date", "industry"]
        )[col].transform(
            lambda x: _zscore_series(x)
        )

    return df


def _zscore_series(x):

    std = x.std()

    if std == 0 or np.isnan(std):
        return pd.Series(np.zeros(len(x)), index=x.index)

    return (x - x.mean()) / (std + 1e-8)


# =========================
# 去均值（用于中性化）
# =========================
def demean(df, cols):

    df = df.copy()

    for col in cols:

        df[col] = df.groupby("trade_date")[col].transform(
            lambda x: x - x.mean()
        )

    return df


def demean_industry(df, cols):

    df = df.copy()

    for col in cols:

        df[col] = df.groupby(
            ["trade_date", "industry"]
        )[col].transform(
            lambda x: x - x.mean()
        )

    return df