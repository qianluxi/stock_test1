"""
fetch_daily_baostock.py

使用 BaoStock 拉取 A 股历史日线行情
- 支持多股票批量拉取
- 支持数据库驱动增量更新
- 使用批量写入提升性能
- 同步日志自动更新
- 不负责 login/logout（由 main 控制）
- 不负责数据库连接生命周期（由 main 控制）
"""

import time
import random
from datetime import datetime
import pandas as pd
import baostock as bs

from db.database import SQLiteDB


# =====================
# 配置
# =====================
SLEEP_RANGE = (0.3, 0.8)


# =====================
# 工具函数
# =====================

def convert_symbol(symbol: str) -> str:
    """
    将 000001 转换为 sz.000001
    将 600000 转换为 sh.600000
    """
    if symbol.startswith("6"):
        return f"sh.{symbol}"
    else:
        return f"sz.{symbol}"


# =====================
# 同步日志更新
# =====================

def update_sync_log(db: SQLiteDB, symbol: str):
    """
    更新 sync_log 表
    """
    df = db.query("""
        SELECT MAX(trade_date) AS max_date,
               COUNT(*) AS cnt
        FROM daily_prices
        WHERE symbol = ?
    """, (symbol,))

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
    """
    增量同步某股票到数据库（数据库驱动）
    由外部控制数据库连接生命周期
    """

    # 1️⃣ 获取数据库已有最大日期
    df_max = db.query(
        "SELECT MAX(trade_date) AS max_date FROM daily_prices WHERE symbol = ?",
        (symbol,)
    )
    max_date = df_max.iloc[0]["max_date"]

    # 如果数据库没有数据，从较早日期开始
    start_date = max_date if max_date else "2010-01-01"

    bs_code = convert_symbol(symbol)

    # 2️⃣ 拉取数据
    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,open,high,low,close,volume,amount",
        start_date=start_date,
        end_date=pd.Timestamp.today().strftime("%Y-%m-%d"),
        frequency="d",
        adjustflag="1",  # 后复权
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

    # 类型转换
    df["trade_date"] = pd.to_datetime(df["date"])
    df["open_adj"] = df["open"].astype(float)
    df["high_adj"] = df["high"].astype(float)
    df["low_adj"] = df["low"].astype(float)
    df["close_adj"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    df["amount"] = df["amount"].astype(float)

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

    # 3️⃣ 真正过滤增量（防止重复）
    if max_date:
        df = df[df["trade_date"] > pd.to_datetime(max_date)]

    if df.empty:
        print(f"[{symbol}] no new data")
        return

    # 4️⃣ 批量写入
    sql_insert = """
    INSERT OR IGNORE INTO daily_prices
    (symbol, trade_date, open_adj, high_adj, low_adj, close_adj, volume, amount)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    data = [
        (
            row["symbol"],
            row["trade_date"].strftime("%Y-%m-%d"),
            row["open_adj"],
            row["high_adj"],
            row["low_adj"],
            row["close_adj"],
            row["volume"],
            row["amount"],
        )
        for _, row in df.iterrows()
    ]

    db.executemany(sql_insert, data)

    # 5️⃣ 更新同步日志
    update_sync_log(db, symbol)

    print(f"[{symbol}] 新增 {len(df)} 行数据")

    # 控制访问节奏
    time.sleep(random.uniform(*SLEEP_RANGE))


# =====================
# 批量同步
# =====================

def sync_stock_pool(symbols: list, db: SQLiteDB):
    """
    批量同步股票池
    由外部控制数据库连接
    """
    for s in symbols:
        sync_daily_prices(s, db)