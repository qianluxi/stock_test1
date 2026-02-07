"""
database.py

SQLite 数据库操作封装
- connect / close
- 执行 SQL
- 查询 DataFrame
- 初始化数据库
"""

import sqlite3
import pandas as pd
from db.schema import ALL_SCHEMA_SQL

class SQLiteDB:
    def __init__(self, db_path="stock.db"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.commit()

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

    def query(self, sql: str, params=None) -> pd.DataFrame:
        """执行查询返回 DataFrame"""
        if params:
            return pd.read_sql(sql, self.conn, params=params)
        else:
            return pd.read_sql(sql, self.conn)

    def init_db(self):
        """建表 + 索引"""
        self.conn.executescript(ALL_SCHEMA_SQL)
        self.conn.commit()
        print(f"[SQLiteDB] 数据库已初始化: {self.db_path}")

