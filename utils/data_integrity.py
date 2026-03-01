import pandas as pd
from db.database import SQLiteDB


def check_data_integrity():

    db = SQLiteDB("stock.db")
    db.connect()

    df = pd.read_sql("""
        SELECT symbol,
               MIN(trade_date) AS start_date,
               MAX(trade_date) AS end_date,
               COUNT(*) AS rows
        FROM daily_prices
        GROUP BY symbol
        ORDER BY symbol
    """, db.conn)

    print("\n===== 数据完整性检查 =====")
    print(df)

    latest_dates = df["end_date"].unique()
    if len(latest_dates) > 1:
        print("\n⚠ 警告：不同股票的最新日期不一致")
    else:
        print("\n✓ 所有股票最新日期一致")

    db.close()