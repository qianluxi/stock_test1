"""
database.py

SQLite 数据库操作封装
- connect / close
- 执行 SQL
- 查询 DataFrame
- 初始化数据库
- 同步日志表管理
"""

import sqlite3
import pandas as pd
from db.schema import ALL_SCHEMA_SQL


class SQLiteDB:
    def __init__(self, db_path=None):
        import os
        # 强制定位到：tushare1/db/stock.db
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "db", "stock.db")
        self.conn = None

    def connect(self):
        """建立数据库连接 + 初始化基础表"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.commit()

        # 自动初始化主表结构
        self.init_db()

        # 自动创建同步日志表
        self.create_sync_log_table()

    def close(self):
        if self.conn:
            self.conn.close()

    def execute(self, sql: str, params=None):
        """执行 SQL（增删改）"""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        self.conn.commit()
        return cursor

    def executemany(self, sql: str, data: list):
        """批量执行（提升写入性能）"""
        cursor = self.conn.cursor()
        cursor.executemany(sql, data)
        self.conn.commit()
        return cursor

    def query(self, sql: str, params=None) -> pd.DataFrame:
        """执行查询返回 DataFrame"""
        if params:
            return pd.read_sql(sql, self.conn, params=params)
        else:
            return pd.read_sql(sql, self.conn)

    def init_db(self):
        """建表 + 索引"""

        cursor = self.conn.cursor()

        for sql in ALL_SCHEMA_SQL:
            cursor.execute(sql)

        self.conn.commit()

        print(f"[SQLiteDB] 数据库已初始化: {self.db_path}")

    def load_data(self, start_date: str, end_date: str):
        sql = """
            SELECT 
                -- 明确指定字段，防止覆盖，保证 close_adj 一定存在
                p.symbol,
                p.trade_date,
                p.open_adj,
                p.high_adj,
                p.low_adj,
                p.close_adj,  # 显式写出，永不丢失
                p.volume,
                p.amount,
                b.industry
            FROM daily_prices p
            LEFT JOIN stock_basic b
            ON substr(p.symbol, 1, 6) = b.symbol
            WHERE p.trade_date BETWEEN ? AND ?
            ORDER BY p.trade_date, p.symbol
        """
        df = self.query(sql, (start_date, end_date))
        return df

    def create_sync_log_table(self):
        """创建数据同步日志表"""
        sql = """
        CREATE TABLE IF NOT EXISTS sync_log (
            symbol TEXT PRIMARY KEY,
            last_sync_date TEXT,
            row_count INTEGER,
            updated_at TEXT
        );
        """
        self.conn.execute(sql)
        self.conn.commit()

    def load_features(self, start_date, end_date):

        sql = """
        SELECT *
        FROM feature_values
        WHERE trade_date BETWEEN ? AND ?
        ORDER BY trade_date
        """

        df = pd.read_sql(sql, self.conn, params=(start_date, end_date))

        return df
    
    def load_prices(self, start_date, end_date):

        sql = """
        SELECT symbol, trade_date, close_adj
        FROM daily_prices
        WHERE trade_date BETWEEN ? AND ?
        """

        df = pd.read_sql(sql, self.conn, params=(start_date, end_date))

        return df
    
    def load_industry(self):

        sql = """
        SELECT symbol, industry
        FROM stock_info
        """

        df = pd.read_sql(sql, self.conn)

        return df