import tushare as ts
import sqlite3
from datetime import datetime
from config import TS_TOKEN

from utils.network import disable_proxy

disable_proxy()

DB_PATH = "db/stock.db"

# 🔑 设置token
ts.set_token(TS_TOKEN)
pro = ts.pro_api()


def load_stock_info():
    print("开始获取股票基础信息（Tushare）...")

    # =========================
    # 1️⃣ 股票基础信息
    # =========================
    df_basic = pro.stock_basic(
        exchange="",
        list_status="L",
        fields="ts_code,symbol,name,industry"
    )

    # =========================
    # 2️⃣ 市值信息（最新一天）
    # =========================
    today = datetime.now().strftime("%Y%m%d")

    try:
        df_mv = pro.daily_basic(
            trade_date=today,
            fields="ts_code,total_mv"
        )
    except Exception:
        print("[WARN] 当日市值获取失败，使用空值")
        df_mv = None

    # =========================
    # 3️⃣ 合并
    # =========================
    if df_mv is not None and not df_mv.empty:
        df = df_basic.merge(df_mv, on="ts_code", how="left")
    else:
        df = df_basic.copy()
        df["total_mv"] = None

    # =========================
    # 4️⃣ 字段统一
    # =========================
    df.rename(columns={
        "symbol": "symbol",
        "name": "name",
        "industry": "industry",
        "total_mv": "market_cap"
    }, inplace=True)

    df = df[["symbol", "name", "industry", "market_cap"]]

    # =========================
    # 5️⃣ 清洗
    # =========================
    df["industry"] = df["industry"].fillna("UNKNOWN")
    df["industry"] = df["industry"].astype(str)

    df["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # =========================
    # 6️⃣ 写入数据库
    # =========================
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ✅ 创建表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_info (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            industry TEXT,
            market_cap REAL,
            updated_at TEXT
        )
    ''')

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT OR REPLACE INTO stock_info
            (symbol, name, industry, market_cap, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            row.symbol,
            row.name,
            row.industry,
            row.market_cap,
            row.updated_at
        ))

    conn.commit()
    conn.close()

    print("stock_info 更新完成（Tushare）")


if __name__ == "__main__":
    load_stock_info()