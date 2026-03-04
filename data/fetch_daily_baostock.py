"""
fetch_daily_baostock.py

强化版：
- 安全数值转换（避免 '' 报错）
- 自动过滤脏数据
- 允许 volume 为 0
- 严格增量控制
- 更安全的日志更新
"""

import time
import random
from datetime import datetime
import pandas as pd
import baostock as bs

from db.database import SQLiteDB


SLEEP_RANGE = (0.3, 0.8)


# =====================
# 工具函数
# =====================

def convert_symbol(symbol: str) -> str:
    if symbol.startswith("6"):
        return f"sh.{symbol}"
    else:
        return f"sz.{symbol}"


# =====================
# 同步日志更新
# =====================

def update_sync_log(db: SQLiteDB, symbol: str):

    df = db.query("""
        SELECT MAX(trade_date) AS max_date,
               COUNT(*) AS cnt
        FROM daily_prices
        WHERE symbol = ?
    """, (symbol,))

    if df.empty:
        return

    max_date = df.iloc[0]["max_date"]
    row_count = df.iloc[0]["cnt"]

    db.execute("""
        INSERT OR REPLACE INTO sync_log
        (symbol, last_sync_date, row_count, updated_at)
        VALUES (?, ?, ?, ?)
    """, (
        symbol,
        max_date,
        row_count,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))


# =====================
# 核心同步函数
# =====================

def sync_daily_prices(symbol: str, db: SQLiteDB):

    df_max = db.query(
        "SELECT MAX(trade_date) AS max_date FROM daily_prices WHERE symbol = ?",
        (symbol,)
    )

    max_date = df_max.iloc[0]["max_date"]
    start_date = max_date if max_date else "2010-01-01"

    bs_code = convert_symbol(symbol)

    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,open,high,low,close,volume,amount",
        start_date=start_date,
        end_date=pd.Timestamp.today().strftime("%Y-%m-%d"),
        frequency="d",
        adjustflag="1",
    )

    if rs.error_code != "0":
        print(f"[{symbol}] 拉取失败:", rs.error_msg)
        return

    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())

    if not data_list:
        print(f"[{symbol}] no new data")
        return

    df = pd.DataFrame(data_list, columns=rs.fields)

    # =====================
    # 安全类型转换（关键修复）
    # =====================

    df["trade_date"] = pd.to_datetime(df["date"], errors="coerce")

    numeric_cols = ["open", "high", "low", "close", "volume", "amount"]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 丢弃没有价格的行
    df = df.dropna(subset=["open", "high", "low", "close"])

    if df.empty:
        print(f"[{symbol}] 全部为无效数据")
        return

    # volume / amount 可为0，但不能为 NaN
    df["volume"] = df["volume"].fillna(0.0)
    df["amount"] = df["amount"].fillna(0.0)

    # 重命名为复权字段
    df["open_adj"] = df["open"]
    df["high_adj"] = df["high"]
    df["low_adj"] = df["low"]
    df["close_adj"] = df["close"]

    df["symbol"] = symbol

    df = df[[
        "symbol",
        "trade_date",
        "open_adj",
        "high_adj",
        "low_adj",
        "close_adj",
        "volume",
        "amount"
    ]]

    # =====================
    # 增量过滤
    # =====================

    if max_date:
        df = df[df["trade_date"] > pd.to_datetime(max_date)]

    if df.empty:
        print(f"[{symbol}] no new data")
        return

    # =====================
    # 批量写入
    # =====================

    sql_insert = """
    INSERT OR IGNORE INTO daily_prices
    (symbol, trade_date, open_adj, high_adj, low_adj, close_adj, volume, amount)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    data = [
        (
            row["symbol"],
            row["trade_date"].strftime("%Y-%m-%d"),
            float(row["open_adj"]),
            float(row["high_adj"]),
            float(row["low_adj"]),
            float(row["close_adj"]),
            float(row["volume"]),
            float(row["amount"]),
        )
        for _, row in df.iterrows()
    ]

    db.executemany(sql_insert, data)

    update_sync_log(db, symbol)

    print(f"[{symbol}] 新增 {len(df)} 行数据")

    time.sleep(random.uniform(*SLEEP_RANGE))


# =====================
# 批量同步
# =====================

def sync_stock_pool(symbols: list, db: SQLiteDB):

    for s in symbols:
        try:
            sync_daily_prices(s, db)
        except Exception as e:
            print(f"[{s}] 同步异常: {e}")