# factors/indicators.py

import pandas as pd
import numpy as np


def add_ma(df: pd.DataFrame, windows=(5, 10, 20)) -> pd.DataFrame:
    """简单移动平均线"""
    for w in windows:
        df[f"ma{w}"] = df["close_adj"].rolling(window=w, min_periods=w).mean()
    return df


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """RSI（Wilder 算法，防未来泄漏）"""
    delta = df["close_adj"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))
    return df


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """MACD（标准定义，EWMA 不用未来数据）"""
    ema_fast = df["close_adj"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close_adj"].ewm(span=slow, adjust=False).mean()

    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    return df


def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    """日收益率（t 对 t-1）"""
    df["ret_1"] = df["close_adj"].pct_change()
    return df


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """统一入口：一次性加所有指标"""
    df = add_ma(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_returns(df)
    return df
