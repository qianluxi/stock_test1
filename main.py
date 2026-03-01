"""
main.py

生产级调度入口：

1️⃣ 判断是否交易日（周末跳过）
2️⃣ 登录 BaoStock
3️⃣ 初始化数据库连接
4️⃣ 批量同步股票池
5️⃣ 数据完整性检查
6️⃣ 抽样做一次指标计算验证
7️⃣ 安全登出 + 关闭数据库
"""

import datetime
import baostock as bs

from db.database import SQLiteDB
from data.fetch_daily_baostock import sync_stock_pool
from factors.indicators import add_all_indicators
from signals.signal_generator import generate_signals
from stock_pool import STOCK_POOL


DB_PATH = "stock.db"


# =========================
# 工具函数
# =========================

def is_weekend() -> bool:
    """
    判断是否周末（简单版本）
    """
    today = datetime.datetime.today().weekday()
    return today >= 5


def check_data_integrity(db: SQLiteDB):
    """
    数据完整性检查（复用同一个数据库连接）
    """
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


def test_indicator_sample(db: SQLiteDB):
    """
    随机抽一只股票做指标验证
    """
    df_symbols = db.query("""
        SELECT symbol
        FROM daily_prices
        GROUP BY symbol
        ORDER BY symbol
    """)

    if df_symbols.empty:
        print("\n数据库为空，无法测试指标")
        return

    test_symbol = df_symbols.iloc[0]["symbol"]
    print(f"\n===== 抽样测试 {test_symbol} 指标计算 =====")

    df = db.query("""
        SELECT trade_date, close_adj
        FROM daily_prices
        WHERE symbol = ?
        ORDER BY trade_date
    """, (test_symbol,))

    df = add_all_indicators(df)
    df = generate_signals(df)

    print("\n===== 最新 5 行数据 =====")
    print(df.tail(5))


# =========================
# 主程序
# =========================

def main():

    # 1️⃣ 交易日判断（可启用）
    # if is_weekend():
    #     print("今天是周末，跳过数据同步")
    #     return

    print("===== 系统启动 =====")

    # 2️⃣ 登录 BaoStock
    print("===== 登录 BaoStock =====")
    lg = bs.login()
    if lg.error_code != "0":
        print("登录失败:", lg.error_msg)
        return
    print("登录成功\n")

    # 3️⃣ 初始化数据库（只连接一次）
    db = SQLiteDB(DB_PATH)
    db.connect()

    try:

        # 4️⃣ 批量同步
        print("===== 开始批量同步股票池 =====")
        sync_stock_pool(STOCK_POOL, db)
        print("===== 同步完成 =====")

        # 5️⃣ 数据完整性检查
        check_data_integrity(db)

        # 6️⃣ 指标抽样测试
        test_indicator_sample(db)

    finally:
        # 7️⃣ 安全释放资源
        db.close()
        bs.logout()
        print("\n===== 已安全关闭数据库并登出 BaoStock =====")


if __name__ == "__main__":
    main()