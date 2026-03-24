import sqlite3

def init_db(db_path="database/stock.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE stock_info (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        industry TEXT,
        market_cap REAL,
        list_date TEXT,
        source TEXT,
        updated_at TEXT
    );
    """)

    conn.commit()
    conn.close()
    print("数据库结构初始化完成")

if __name__ == "__main__":
    init_db()