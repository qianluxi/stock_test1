# tools/generate_stock_pool.py

import sqlite3
import os
import pandas as pd


DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "db",
    "stock.db"
)

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "stock_pool.py"
)


def load_data():
    print("连接数据库:", DB_PATH)
    conn = sqlite3.connect(DB_PATH)

    df_basic = pd.read_sql("SELECT * FROM stock_basic", conn)
    df_mv = pd.read_sql("SELECT * FROM daily_basic", conn)

    conn.close()

    print("stock_basic 行数:", len(df_basic))
    print("daily_basic 行数:", len(df_mv))

    # 合并
    df = pd.merge(df_basic, df_mv, on="ts_code", how="inner")

    # total_mv 单位：万元 → 转换为亿元
    df["total_mv"] = df["total_mv"] / 10000

    print("合并后行数:", len(df))

    return df


def choose_industry(df):
    industries = sorted(df["industry"].dropna().unique())

    print("\n可选行业：")
    for i, ind in enumerate(industries):
        print(f"{i}. {ind}")

    idx = int(input("\n请选择行业编号: "))
    selected = industries[idx]

    print("选择行业:", selected)

    return selected


def choose_market_cap():
    min_cap = float(input("请输入最小市值(亿): "))
    max_cap = float(input("请输入最大市值(亿): "))
    return min_cap, max_cap


def generate_pool(df, industry, min_cap, max_cap):
    df_filtered = df[
        (df["industry"] == industry) &
        (df["total_mv"] >= min_cap) &
        (df["total_mv"] <= max_cap)
    ]

    print("筛选后股票数:", len(df_filtered))

    if len(df_filtered) == 0:
        print("⚠ 没有符合条件的股票")
        return []

    # 按市值降序
    df_filtered = df_filtered.sort_values("total_mv", ascending=False)

    # 取前300
    df_filtered = df_filtered.head(300)

    return df_filtered["ts_code"].tolist()


def save_stock_pool(stock_list):
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("# 自动生成股票池\n")
        f.write("STOCK_POOL = [\n")

        for code in stock_list:
            f.write(f"    '{code}',\n")

        f.write("]\n")

    print("✅ stock_pool.py 已生成")
    print("股票数量:", len(stock_list))


def main():
    df = load_data()

    industry = choose_industry(df)
    min_cap, max_cap = choose_market_cap()

    stock_list = generate_pool(df, industry, min_cap, max_cap)

    if stock_list:
        save_stock_pool(stock_list)


if __name__ == "__main__":
    main()