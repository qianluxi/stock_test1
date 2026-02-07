"""
fetch_daily.py

从 AkShare 拉取 A 股历史日线行情
- 支持多股票批量拉取
- 支持增量更新
- 数据直接写入 SQLite 数据库
"""

import os
import pandas as pd
import akshare as ak
from db.database import SQLiteDB

DB_PATH = "stock.db"
db = SQLiteDB(DB_PATH)
db.connect()
db.init_db()

def fetch_stock_daily(symbol: str) -> pd.DataFrame:
    """
    从 AkShare 拉取某股票的日线行情
    """
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
        df.rename(columns={
            "日期": "trade_date",
            "开盘": "open_adj",
            "最高": "high_adj",
            "最低": "low_adj",
            "收盘": "close_adj",
            "成交量": "volume",
            "成交额": "amount"
        }, inplace=True)
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
        df = df[["trade_date", "open_adj", "high_adj", "low_adj", "close_adj", "volume", "amount"]]
        df["symbol"] = symbol
        df = df[["symbol", "trade_date", "open_adj", "high_adj", "low_adj", "close_adj", "volume", "amount"]]
        df.sort_values("trade_date", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
    except Exception as e:
        print(f"[{symbol}] 拉取失败: {e}")
        return pd.DataFrame()

def sync_daily_prices(symbol: str):
    """
    增量同步某股票到数据库
    """
    # 查询数据库已有的最大 trade_date
    sql = "SELECT MAX(trade_date) FROM daily_prices WHERE symbol = ?"
    df_max = db.query(sql, params=(symbol,))
    max_date = df_max.iloc[0, 0]  # None 或 YYYY-MM-DD

    # 拉取数据
    df = fetch_stock_daily(symbol)
    if df.empty:
        return

    if max_date:
        df = df[df["trade_date"] > max_date]

    if df.empty:
        print(f"[{symbol}] no new data")
        return

    # 写入数据库
    for _, row in df.iterrows():
        sql_insert = """
        INSERT OR REPLACE INTO daily_prices
        (symbol, trade_date, open_adj, high_adj, low_adj, close_adj, volume, amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        db.execute(sql_insert, tuple(row))
    print(f"[{symbol}] 新增 {len(df)} 行数据")

def sync_stock_pool(symbols: list):
    """
    批量增量拉取股票
    """
    for s in symbols:
        sync_daily_prices(s)

if __name__ == "__main__":
    stock_pool = ["600519", "000001", "000002"]
    sync_stock_pool(stock_pool)

    db.close()
