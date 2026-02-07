# features/build_features.py

import pandas as pd
from db.database import SQLiteDB
from factors.indicators import add_all_indicators

DB_PATH = "stock.db"


def load_daily_prices(symbol: str) -> pd.DataFrame:
    """从数据库加载某股票日线数据"""
    db = SQLiteDB(DB_PATH)
    db.connect()

    sql = """
    SELECT
        trade_date,
        symbol,
        close_adj
    FROM daily_prices
    WHERE symbol = ?
    ORDER BY trade_date
    """
    df = db.query(sql, params=(symbol,))
    db.close()

    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def build_features(symbol: str) -> pd.DataFrame:
    """
    构建 ML 特征 + 标签
    label = 明天是否上涨
    """
    df = load_daily_prices(symbol)

    if df.empty:
        raise ValueError(f"{symbol} 无数据")

    # === 技术指标 ===
    df = add_all_indicators(df)

    # === 标签（唯一允许的未来信息）===
    df["label"] = (df["close_adj"].shift(-1) > df["close_adj"]).astype(int)

    # === 丢掉不可用行 ===
    feature_cols = [
        "ma5", "ma10", "ma20",
        "rsi",
        "macd", "macd_signal", "macd_hist",
        "ret_1",
        "label"
    ]

    df_ml = df.dropna(subset=feature_cols).reset_index(drop=True)

    return df_ml


if __name__ == "__main__":
    symbol = "002264"
    df = build_features(symbol)

    print(f"[{symbol}] 特征样本数: {len(df)}")
    print(df.tail(5))
