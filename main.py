"""
main.py

生产 + Alpha研究统一入口

流程：

1️⃣ 判断是否交易日
2️⃣ 登录 BaoStock
3️⃣ 初始化数据库连接
4️⃣ 批量同步股票池
5️⃣ 数据完整性检查
6️⃣ AlphaPipeline 回归预测 + IC评估
7️⃣ 安全释放资源
"""

from utils.network import disable_proxy

disable_proxy()

import datetime
import baostock as bs

from db.database import SQLiteDB
from data.fetch_daily_baostock import sync_stock_pool
from factors.indicators import add_all_indicators
from stock_pool import STOCK_POOL

from alpha.pipeline import AlphaPipeline
from alpha.walkforward import WalkForwardEngine


DB_PATH = "stock.db"


# =========================
# 工具函数
# =========================

def is_weekend() -> bool:
    today = datetime.datetime.today().weekday()
    return today >= 5


def check_data_integrity(db: SQLiteDB):

    df = db.query("""
        SELECT symbol,
               MIN(trade_date) AS start_date,
               MAX(trade_date) AS end_date,
               COUNT(*) AS rows
        FROM daily_prices
        GROUP BY symbol
        ORDER BY symbol
    """)

    print("\n===== 数据完整性检查 =====")
    print(df)

    if df.empty:
        print("\n⚠ 数据库为空")
        return

    latest_dates = df["end_date"].unique()
    if len(latest_dates) > 1:
        print("\n⚠ 警告：不同股票最新日期不一致")
    else:
        print("\n✓ 所有股票最新日期一致")


# =========================
# Feature Builder
# =========================

def build_features(df):
    """
    AlphaPipeline 使用的统一特征入口
    """
    df = add_all_indicators(df)

    # 删除原始信号列（旧系统遗留）
    if "signal" in df.columns:
        df = df.drop(columns=["signal"])

    return df


# =========================
# 主程序
# =========================

def main():

    # if is_weekend():
    #     print("今天是周末，跳过数据同步")
    #     return

    print("===== 系统启动 =====")

    # 1️⃣ 登录 BaoStock
    print("===== 登录 BaoStock =====")
    lg = bs.login()
    if lg.error_code != "0":
        print("登录失败:", lg.error_msg)
        return
    print("登录成功\n")

    # 2️⃣ 初始化数据库
    db = SQLiteDB(DB_PATH)
    db.connect()

    try:

        # =========================
        # 数据同步阶段
        # =========================

        print("===== 开始批量同步股票池 =====")
        sync_stock_pool(STOCK_POOL, db)
        print("===== 同步完成 =====")

        # 数据完整性检查
        check_data_integrity(db)

        # =========================
        # Alpha 研究阶段
        # =========================
        print("\n===== 数据检查完成，开始 Alpha 研究 =====")
        print("\n===== 启动 Walk-Forward v1.4 =====")

        pipeline = AlphaPipeline(
            db=db,
            feature_builder=build_features
        )

        wf = WalkForwardEngine(pipeline)

        report, predictions = wf.run(
            start_date="2018-01-01",
            end_date="2026-03-03",
            train_years=5,
            test_years=1,
            horizon=5
        )

        print("\n===== Walk-Forward 评估报告 =====")
        for k, v in report.items():
            print(f"{k}: {v:.6f}")

        print("\n===== 最新预测样例 =====")
        print(predictions.tail(10))

    finally:
        db.close()
        bs.logout()
        print("\n===== 已安全关闭数据库并登出 BaoStock =====")


if __name__ == "__main__":
    main()