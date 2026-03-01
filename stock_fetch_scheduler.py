import time
import random
import json
from datetime import datetime, timedelta, date
from pathlib import Path

import akshare as ak
import sqlite3
from stock_pool import STOCK_POOL

BATCH_SIZE = 4
STOCK_INTERVAL_RANGE = (62, 93)
BATCH_INTERVAL = 930
DB_PATH = "stock.db"
FAILED_FILE = Path("failed_stocks.json")
TABLE_NAME = "stock_daily"
HIST_YEARS = 3


class StockFetchScheduler:
    def __init__(self, stock_list):
        self.stock_list = stock_list
        self.failed_today = self._load_failed_today()
        self.conn = sqlite3.connect(DB_PATH)
        self._ensure_index()

    # ================= 主调度 =================
    def run(self):
        pending = [
            s for s in self.stock_list
            if s not in self.failed_today
        ]
        print(f"待拉取股票数: {len(pending)}")

        idx = 0
        batch_no = 1

        while idx < len(pending):
            batch = pending[idx: idx + BATCH_SIZE]
            print(f"\n===== 批次 {batch_no} | {batch} =====")

            for stock_code in batch:
                self._fetch_single(stock_code)
                sleep_sec = random.uniform(*STOCK_INTERVAL_RANGE)
                time.sleep(sleep_sec)

            idx += BATCH_SIZE
            batch_no += 1

            if idx < len(pending):
                time.sleep(BATCH_INTERVAL)

        print("任务结束")

    # ================= 单股票拉取 =================
    def _fetch_single(self, stock_code):
        try:
            last_date = self._get_last_date(stock_code)

            if last_date:
                start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                start_date = (
                    datetime.today() - timedelta(days=HIST_YEARS * 365)
                ).strftime("%Y-%m-%d")

            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                adjust="qfq"
            )

            if df is None or df.empty:
                print(f"[{stock_code}] 无新增数据")
                return

            self._insert_to_db(stock_code, df)
            print(f"[{stock_code}] 新增 {len(df)} 行")

        except Exception as e:
            print(f"[{stock_code}] 失败: {e}")
            self._record_failed(stock_code, e)

    # ================= 查询最后日期 =================
    def _get_last_date(self, stock_code):
        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT MAX(日期) FROM {TABLE_NAME} WHERE 股票代码=?",
            (stock_code,)
        )
        result = cursor.fetchone()[0]
        if result:
            return datetime.strptime(result, "%Y-%m-%d")
        return None

    # ================= 写入数据库 =================
    def _insert_to_db(self, stock_code, df):
        df = df.copy()
        df["股票代码"] = stock_code

        # 转换日期格式
        df["日期"] = df["日期"].astype(str)

        # 去重（删除已有数据）
        dates = df["日期"].tolist()
        placeholders = ",".join("?" * len(dates))

        self.conn.execute(
            f"""
            DELETE FROM {TABLE_NAME}
            WHERE 股票代码=? AND 日期 IN ({placeholders})
            """,
            (stock_code, *dates)
        )

        df.to_sql(
            TABLE_NAME,
            self.conn,
            if_exists="append",
            index=False
        )
        self.conn.commit()

    # ================= 建索引 =================
    def _ensure_index(self):
        cursor = self.conn.cursor()
        cursor.execute(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_date_code
            ON {TABLE_NAME} (日期, 股票代码)
        """)
        self.conn.commit()

    # ================= 失败记录 =================
    def _record_failed(self, stock_code, reason):
        record = {
            "stock": stock_code,
            "reason": str(reason),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        data = []
        if FAILED_FILE.exists():
            data = json.loads(FAILED_FILE.read_text(encoding="utf-8"))

        data.append(record)
        FAILED_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def _load_failed_today(self):
        if not FAILED_FILE.exists():
            return set()
        today = date.today().isoformat()
        data = json.loads(FAILED_FILE.read_text(encoding="utf-8"))
        return {r["stock"] for r in data if r["date"].startswith(today)}


if __name__ == "__main__":
    scheduler = StockFetchScheduler(STOCK_POOL)
    scheduler.run()
