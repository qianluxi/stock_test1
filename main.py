"""
main.py

演示流程：
daily_prices -> factors -> signal_generator
"""

import pandas as pd
from db.database import SQLiteDB
from factors.indicators import add_all_indicators
from signals.signal_generator import generate_signals
from data.fetch_daily import sync_daily_prices

def main():
    # 1️⃣ 拉数据（增量同步）
    
    symbols = ["001229"]  # 可扩展股票池
    for s in symbols:
        sync_daily_prices(s)

    # 2️⃣ 读取数据
    db = SQLiteDB("stock.db")
    db.connect()

    df = pd.read_sql(
        """
        SELECT trade_date, close_adj
        FROM daily_prices
        WHERE symbol = '001229'
        ORDER BY trade_date
        """,
        db.conn
    )

    # 3️⃣ 计算指标
    df = add_all_indicators(df)

    # 4️⃣ 生成信号（占位）
    df = generate_signals(df)

    print(df.tail(10))

if __name__ == "__main__":
    main()
