"""
fetch_daily_tushare.py

强化版：
- Tushare日线
- 增量更新
- 安全类型转换
- 自动处理复权字段
- 严格异常捕获
"""
from utils.network import disable_proxy

disable_proxy()

import time
import random
from datetime import datetime
import pandas as pd
import tushare as ts
from stock_pool import STOCK_POOL
from db.database import SQLiteDB
from config import TS_TOKEN


SLEEP_RANGE = (0.2, 0.5)


# ==========================
# 初始化 Tushare
# ==========================

def init_tushare(token: str):
    ts.set_token(token)
    return ts.pro_api()


# ==========================
# 同步日志更新
# ==========================

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


# ==========================
# 核心同步函数
# ==========================

def sync_daily_prices(symbol: str, db: SQLiteDB, pro):

    # 查数据库已有最大日期
    df_max = db.query(
        "SELECT MAX(trade_date) AS max_date FROM daily_prices WHERE symbol = ?",
        (symbol,)
    )

    max_date = df_max.iloc[0]["max_date"]

    if max_date and pd.notna(max_date):
        start_date = pd.to_datetime(max_date).strftime("%Y%m%d")
    else:
        start_date = "20100101"

    end_date = datetime.today().strftime("%Y%m%d")

    print(f"[{symbol}] 拉取 {start_date} - {end_date}")

    try:
        df = pro.daily(
            ts_code=symbol,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        print(f"[{symbol}] Tushare接口异常:", e)
        return

    if df is None or df.empty:
        print(f"[{symbol}] 无新数据")
        return

    # ==========================
    # 数据清洗
    # ==========================

    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")

    numeric_cols = [
        "open", "high", "low", "close",
        "vol", "amount"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["open", "high", "low", "close"])

    if df.empty:
        print(f"[{symbol}] 全为无效数据")
        return

    # Tushare vol 单位：手 → 转为股
    df["volume"] = df["vol"] * 100
    df["amount"] = df["amount"]

    # 统一为复权字段（当前为未复权）
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

    # ==========================
    # 增量过滤
    # ==========================

    if max_date:
        max_date = pd.to_datetime(max_date)
        df = df[df["trade_date"] > max_date]

    if df.empty:
        print(f"[{symbol}] 无增量数据")
        return

    # ==========================
    # 排序
    # ==========================

    df = df.sort_values("trade_date")

    # ==========================
    # 批量写入
    # ==========================

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

    print(f"[{symbol}] 新增 {len(df)} 行")

    time.sleep(random.uniform(*SLEEP_RANGE))


# ==========================
# 批量同步
# ==========================

def sync_stock_pool(symbols: list, db: SQLiteDB, token: str):

    pro = init_tushare(token)

    print(f"股票数量: {len(symbols)}")

    for s in symbols:
        try:
            sync_daily_prices(s, db, pro)
        except Exception as e:
            print(f"[{s}] 同步异常:", e)

# ==========================
# 程序入口
# ==========================

# ==========================
# 程序入口
# ==========================

if __name__ == "__main__":

    print("===== 日线数据同步开始 =====")

    TOKEN = TS_TOKEN

    db = SQLiteDB("db/stock.db")

    db.connect()

    print(f"股票数量: {len(STOCK_POOL)}")

    sync_stock_pool(STOCK_POOL, db, TOKEN)

    db.close()

    print("===== 日线同步完成 =====")