import sqlite3

conn = sqlite3.connect("stock.db")
cursor = conn.cursor()

cursor.execute("""
DELETE FROM stock_daily
WHERE rowid NOT IN (
    SELECT MIN(rowid)
    FROM stock_daily
    GROUP BY 日期, 股票代码
)
""")

conn.commit()
conn.close()

print("重复数据已清理")
