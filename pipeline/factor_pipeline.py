import pandas as pd
from datetime import datetime, timedelta

from db.database import SQLiteDB
from factors.indicator_engine import IndicatorEngine
from factors.factor_writer import write_factors

from features.feature_builder import FeatureBuilder
from features.feature_writer import write_features

from stock_pool import STOCK_POOL


class FactorPipeline:

    def __init__(self, db_path="db/stock.db"):

        self.db = SQLiteDB(db_path)
        self.db.connect()

        self.engine = IndicatorEngine()
        self.feature_builder = FeatureBuilder()

        # 回溯窗口（必须覆盖最大因子窗口）
        self.LOOKBACK_DAYS = 180


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
    # 拉取行情数据（含行业）
    # ============================
    def load_price_data(self, symbol, start_date):

        sql = """
        SELECT p.*, i.industry
        FROM daily_prices p
        LEFT JOIN stock_info i
        ON p.symbol = i.symbol
        WHERE p.symbol = ?
        AND p.trade_date >= ?
        ORDER BY p.trade_date
        """

        df = pd.read_sql(sql, self.db.conn, params=(symbol, start_date))

        # ✅ 行业缺失填充（避免中性化出错）
        if "industry" in df.columns:
            df["industry"] = df["industry"].fillna("UNKNOWN")

        return df


    # ============================
    # 收集所有股票数据（核心）
    # ============================
    def collect_all_data(self):

        all_df = []
        failed = []

        for symbol in STOCK_POOL:

            try:
                print(f"\n[Pipeline] 处理股票: {symbol}")

                last_date = self.get_last_factor_date(symbol)

                if last_date:
                    print(f"[Pipeline] 已有因子数据，最后日期: {last_date}")

                    dt = datetime.strptime(last_date, "%Y-%m-%d")
                    start_date = (dt - timedelta(days=self.LOOKBACK_DAYS)).strftime("%Y-%m-%d")
                else:
                    print("[Pipeline] 首次计算")
                    start_date = "2010-01-01"

                df = self.load_price_data(symbol, start_date)

                if df.empty:
                    print("[Pipeline] 无行情数据，跳过")
                    continue

                # 计算因子
                df = self.engine.compute_all(df)

                # ✅ 写入 factor_values（保证链路不断）
                write_factors(self.db, df)

                # 只保留新增部分（用于Feature）
                if last_date:
                    df = df[df["trade_date"] > last_date]

                if df.empty:
                    print("[Pipeline] 无新增因子")
                    continue

                all_df.append(df)

            except Exception as e:
                print(f"[ERROR] {symbol} 失败:", e)
                failed.append(symbol)

        if failed:
            print("\n[WARNING] 失败股票列表:", failed)

        if not all_df:
            return pd.DataFrame()

        df = pd.concat(all_df, ignore_index=True)

        # ============================
        # 🚨 横截面完整性修复（关键）
        # ============================

        # 转换日期类型
        df["trade_date"] = pd.to_datetime(df["trade_date"])

        # 每天股票数量统计
        counts = df.groupby("trade_date")["symbol"].nunique()

        # 保留至少80%股票存在的日期
        valid_dates = counts[counts > len(STOCK_POOL) * 0.8].index

        df = df[df["trade_date"].isin(valid_dates)]

        # 转回字符串（兼容后续模块）
        df["trade_date"] = df["trade_date"].dt.strftime("%Y-%m-%d")

        return df


    # ============================
    # 主入口
    # ============================
    def run(self):

        print("===== 因子流水线开始 =====")

        # 1️⃣ 收集全市场数据
        df = self.collect_all_data()

        if df.empty:
            print("[Pipeline] 无数据可处理")
            self.db.close()
            return

        print(f"\n[Pipeline] 总数据量: {len(df)}")

        # ============================
        # ✅ 排序（保证稳定性）
        # ============================
        df = df.sort_values(["trade_date", "symbol"]).reset_index(drop=True)

        # ============================
        # 2️⃣ 构建特征（核心）
        # ============================
        df = self.feature_builder.build(df)

        print("[Pipeline] FeatureBuilder 完成")

        # ============================
        # 3️⃣ 写入数据库
        # ============================
        write_features(self.db, df)

        print("===== 因子流水线结束 =====")

        self.db.close()


# ============================
# CLI入口
# ============================
if __name__ == "__main__":

    pipeline = FactorPipeline()
    pipeline.run()