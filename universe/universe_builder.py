"""
universe_builder.py

交互式生成股票池
按行业 + 市值区间筛选
"""

import pandas as pd
from datetime import datetime
from db.database import SQLiteDB

DB_PATH = "stock.db"
MAX_STOCKS = 300


def build_universe():

    db = SQLiteDB(DB_PATH)
    db.connect()

    print("===== 股票池生成器 =====")

    industry = input("请输入行业名称（如 航天）：").strip()
    cap_min = float(input("请输入市值下限（单位：亿）：").strip())
    cap_max = float(input("请输入市值上限（单位：亿）：").strip())

    print("\n筛选中...")

    df = db.query("""
        SELECT s.symbol, s.industry, s.market_cap
        FROM stock_info s
        WHERE s.industry LIKE ?
        AND s.market_cap BETWEEN ? AND ?
    """, (f"%{industry}%", cap_min * 1e8, cap_max * 1e8))

    if df.empty:
        print("无符合条件股票")
        return

    # 再过滤上市时间 >= 250天
    list_df = db.query("""
        SELECT symbol, MIN(trade_date) as start_date
        FROM daily_prices
        GROUP BY symbol
    """)

    list_df["start_date"] = pd.to_datetime(list_df["start_date"])
    list_df["list_days"] = (datetime.now() - list_df["start_date"]).dt.days

    df = df.merge(list_df[["symbol", "list_days"]], on="symbol")
    df = df[df["list_days"] >= 250]

    # 按市值排序
    df = df.sort_values("market_cap", ascending=False)

    df = df.head(MAX_STOCKS)

    symbols = df["symbol"].tolist()

    print(f"最终股票数量: {len(symbols)}")

    # 写入 stock_pool.py
    with open("stock_pool.py", "w", encoding="utf-8") as f:
        f.write("# 自动生成，请勿手动修改\n")
        f.write("STOCK_POOL = [\n")
        for s in symbols:
            f.write(f'    "{s}",\n')
        f.write("]\n")

    # 写入数据库记录
    universe_name = f"{industry}_{cap_min}_{cap_max}_{datetime.now().strftime('%Y%m%d')}"

    for s in symbols:
        db.execute("""
            INSERT INTO stock_universe (universe_name, symbol, created_at)
            VALUES (?, ?, ?)
        """, (universe_name, s, datetime.now()))

    db.close()

    print("股票池生成完成")
    print("请运行 main.py 进行回测")


if __name__ == "__main__":
    build_universe()