"""
cleanup.py

数据库清理工具
- 删除无用股票数据
- 删除指定日期范围的数据
"""

from db.database import SQLiteDB

def delete_stock(symbol: str, db_path="stock.db"):
    """
    删除某个股票的全部数据
    """
    db = SQLiteDB(db_path)
    db.connect()
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_prices WHERE symbol = ?", (symbol,))
    total = cursor.fetchone()[0]

    if total == 0:
        print(f"{symbol} 数据不存在，无需删除")
        return

    cursor.execute("DELETE FROM daily_prices WHERE symbol = ?", (symbol,))
    db.conn.commit()
    print(f"{symbol} 数据已删除，共 {total} 行")


def delete_stock_date_range(symbol: str, start_date: str, end_date: str, db_path="stock.db"):
    """
    删除某股票指定日期范围的数据
    日期格式: 'YYYY-MM-DD'
    """
    db = SQLiteDB(db_path)
    db.connect()
    
    cursor = db.conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM daily_prices WHERE symbol = ? AND trade_date BETWEEN ? AND ?",
        (symbol, start_date, end_date)
    )
    total = cursor.fetchone()[0]

    if total == 0:
        print(f"{symbol} 在 {start_date} ~ {end_date} 范围内没有数据，无需删除")
        return

    cursor.execute(
        "DELETE FROM daily_prices WHERE symbol = ? AND trade_date BETWEEN ? AND ?",
        (symbol, start_date, end_date)
    )
    db.conn.commit()
    print(f"{symbol} 在 {start_date} ~ {end_date} 范围内已删除 {total} 行")
