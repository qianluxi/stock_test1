# data/data_loader_tushare.py

import os
# 禁用系统代理
from utils.network import disable_proxy

disable_proxy()

import tushare as ts
import pandas as pd
import sqlite3
import traceback
from datetime import datetime
from config import TS_TOKEN

class TushareDataLoader:

    def __init__(self, token, db_path):
        print("=" * 60)
        print("初始化 TushareDataLoader")

        self.token = token
        self.db_path = db_path

        print(f"数据库路径: {self.db_path}")

        ts.set_token(self.token)
        self.pro = ts.pro_api()

        # 测试token是否可用
        try:
            test_df = self.pro.query("stock_basic", limit=1)
            print("Token 测试成功")
        except Exception as e:
            print("❌ Token 测试失败")
            print(e)
            raise

        # 建立数据库连接
        self.conn = sqlite3.connect(self.db_path)
        print("数据库连接成功")
        print("=" * 60)

    # -------------------------------------------------
    # 下载股票基础信息
    # -------------------------------------------------
    def download_stock_basic(self):
        print("\n开始下载 stock_basic ...")

        try:
            df = self.pro.query(
                "stock_basic",
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,area,industry,market,list_date"
            )

            print(f"返回记录数: {len(df)}")

            if df.empty:
                print("⚠ stock_basic 返回空数据")
                print("列名:", df.columns.tolist())
                return

            print("列名:", df.columns.tolist())
            print("前5行数据:")
            print(df.head())

            df.to_sql("stock_basic", self.conn, if_exists="replace", index=False)

            print(f"✅ stock_basic 已写入数据库，共 {len(df)} 条")

        except Exception as e:
            print("❌ stock_basic 下载失败")
            traceback.print_exc()

    # -------------------------------------------------
    # 获取最近交易日
    # -------------------------------------------------
    def get_latest_trade_day(self):
        print("\n获取最近交易日...")

        try:
            today = datetime.today().strftime("%Y%m%d")

            df = self.pro.query(
                "trade_cal",
                exchange="SSE",
                start_date="20220101",
                end_date=today,
                fields="exchange,cal_date,is_open,pretrade_date"
            )

            print(f"trade_cal 返回记录数: {len(df)}")

            if df.empty:
                print("❌ trade_cal 返回空数据")
                return None

            print("列名:", df.columns.tolist())
            print("前5行:")
            print(df.head())

            if "is_open" not in df.columns:
                print("❌ trade_cal 数据中没有 is_open 字段")
                return None

            open_days = df[df["is_open"] == 1]

            if open_days.empty:
                print("❌ 没有找到开放交易日")
                return None

            latest_day = open_days["cal_date"].max()

            print(f"最近交易日: {latest_day}")

            return latest_day

        except Exception as e:
            print("❌ 获取交易日失败")
            traceback.print_exc()
            return None

    # -------------------------------------------------
    # 更新市值信息
    # -------------------------------------------------
    def update_market_cap(self):
        print("\n开始更新市值 ...")

        trade_date = self.get_latest_trade_day()

        if trade_date is None:
            print("❌ 无法获取交易日，终止市值更新")
            return

        try:
            df = self.pro.query(
                "daily_basic",
                trade_date=trade_date,
                fields="ts_code,trade_date,total_mv,circ_mv"
            )

            print(f"daily_basic 返回记录数: {len(df)}")

            if df.empty:
                print("⚠ daily_basic 返回空数据")
                return

            print("列名:", df.columns.tolist())
            print("前5行:")
            print(df.head())

            df.to_sql("daily_basic", self.conn, if_exists="replace", index=False)

            print(f"✅ 市值数据已写入数据库，共 {len(df)} 条")

        except Exception as e:
            print("❌ 市值更新失败")
            traceback.print_exc()

    # -------------------------------------------------
    def close(self):
        self.conn.close()
        print("\n数据库已关闭")


# ====================================================
# 直接运行测试
# ====================================================
if __name__ == "__main__":

    TOKEN = TS_TOKEN
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "db", "stock.db")

    loader = TushareDataLoader(TOKEN, DB_PATH)

    loader.download_stock_basic()
    loader.update_market_cap()

    loader.close()