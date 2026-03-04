"""
stock_universe_builder.py

根据规则生成 stock_pool.py
可独立运行
"""

# 修复路径问题，放在代码第一行！
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))  # 把项目根目录加入路径
import pandas as pd
from datetime import datetime, timedelta
from db.database import SQLiteDB

DB_PATH = "stock.db"

MIN_LIST_DAYS = 250
MIN_AVG_AMOUNT = 50_000_000   # 5000万
MAX_STOCKS = 300


def build_stock_pool():

    db = SQLiteDB(DB_PATH)
    db.connect()

    print("===== 构建股票池 =====")

    # 1️⃣ 获取每只股票基础统计
    df = db.query("""
        SELECT
            symbol,
            MIN(trade_date) AS start_date,
            MAX(trade_date) AS end_date,
            COUNT(*) AS rows
        FROM daily_prices
        GROUP BY symbol
    """)

    if df.empty:
        print("数据库无数据")
        return

    # 2️⃣ 上市时间过滤
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["list_days"] = (datetime.now() - df["start_date"]).dt.days

    df = df[df["list_days"] >= MIN_LIST_DAYS]

    # 3️⃣ 流动性过滤（最近60日平均成交额）
    liquidity_df = db.query("""
        SELECT symbol, AVG(amount) AS avg_amount
        FROM (
            SELECT *
            FROM daily_prices
            WHERE trade_date >= date('now', '-60 day')
        )
        GROUP BY symbol
    """)

    df = df.merge(liquidity_df, on="symbol", how="left")
    df = df[df["avg_amount"] >= MIN_AVG_AMOUNT]

    # 4️⃣ 排序（按成交额）
    df = df.sort_values("avg_amount", ascending=False)

    df = df.head(MAX_STOCKS)

    symbols = df["symbol"].tolist()

    print(f"筛选后股票数量: {len(symbols)}")

    db.close()

    generate_stock_pool_file(symbols)


def generate_stock_pool_file(symbols):

    print("生成 stock_pool.py")

    with open("stock_pool.py", "w", encoding="utf-8") as f:
        f.write("# 自动生成，请勿手动修改\n")
        f.write("STOCK_POOL = [\n")
        for s in symbols:
            f.write(f'    "{s}",\n')
        f.write("]\n")

    print("stock_pool.py 已更新")


if __name__ == "__main__":
    build_stock_pool()