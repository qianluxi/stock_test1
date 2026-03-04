import akshare as ak
import sqlite3
from datetime import datetime

DB_PATH = "database/stock.db"

def load_stock_info():
    print("开始获取股票基础信息...")

    # 获取A股实时行情（包含市值）
    df = ak.stock_zh_a_spot_em()

    # 重要字段：
    # 代码
    # 名称
    # 总市值
    # 所属行业

    df = df[[
        "代码",
        "名称",
        "所属行业",
        "总市值"
    ]]

    df.columns = [
        "symbol",
        "name",
        "industry",
        "market_cap"
    ]

    df["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

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

    print("stock_info 更新完成")

if __name__ == "__main__":
    load_stock_info()