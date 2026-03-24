import pandas as pd
from datetime import datetime, timedelta

from db.database import SQLiteDB
from factors.indicator_engine import IndicatorEngine
from factors.factor_writer import write_factors

# 如果你用 stock_pool.py
from stock_pool import STOCK_POOL


class FactorPipeline:

    def __init__(self, db_path="db/stock.db"):

        self.db = SQLiteDB(db_path)
        self.db.connect()

        self.engine = IndicatorEngine()


    # ============================
    # 获取某只股票最后已计算日期
    # ============================

    def get_last_factor_date(self, symbol):

        sql = """
        SELECT MAX(trade_date) as max_date
        FROM factor_values
        WHERE symbol = ?
        """

        df = pd.read_sql(sql, self.db.conn, params=(symbol,))

        if df["max_date"].iloc[0] is None:
            return None

        return df["max_date"].iloc[0]


    # ============================
    # 拉取行情数据
    # ============================

    def load_price_data(self, symbol, start_date):

        sql = """
        SELECT *
        FROM daily_prices
        WHERE symbol = ?
        AND trade_date >= ?
        ORDER BY trade_date
        """

        df = pd.read_sql(sql, self.db.conn, params=(symbol, start_date))

        return df


    # ============================
    # 单只股票处理
    # ============================

    def process_symbol(self, symbol):

        print(f"\n[Pipeline] 处理股票: {symbol}")

        last_date = self.get_last_factor_date(symbol)

        if last_date:
            print(f"[Pipeline] 已有因子数据，最后日期: {last_date}")

            # ⚠️ 往前多取60天（解决MA/ATR窗口问题）
            dt = datetime.strptime(last_date, "%Y-%m-%d")
            start_date = (dt - timedelta(days=120)).strftime("%Y-%m-%d")
        else:
            print("[Pipeline] 首次计算")

            start_date = "2010-01-01"

        df = self.load_price_data(symbol, start_date)

        if df.empty:
            print("[Pipeline] 无行情数据，跳过")
            return

        print(f"[Pipeline] 行情条数: {len(df)}")

        df = self.engine.compute_all(df)

        # 只保留新数据
        if last_date:
            df = df[df["trade_date"] > last_date]

        if df.empty:
            print("[Pipeline] 无新增因子")
            return

        write_factors(self.db, df)

        print(f"[Pipeline] 完成 {symbol}")


    # ============================
    # 主入口
    # ============================

    def run(self):

        print("===== 因子流水线开始 =====")

        for symbol in STOCK_POOL:

            try:
                self.process_symbol(symbol)
            except Exception as e:
                print(f"[ERROR] {symbol} 失败:", e)

        print("===== 因子流水线结束 =====")

        self.db.close()


# ============================
# CLI入口
# ============================

if __name__ == "__main__":

    pipeline = FactorPipeline()

    pipeline.run()