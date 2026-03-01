"""
fetch_examp.py

测试 BaoStock 日线行情拉取是否正常
"""

import pandas as pd
import baostock as bs


def convert_symbol(symbol: str) -> str:
    """
    000001 -> sz.000001
    600000 -> sh.600000
    """
    if symbol.startswith("6"):
        return f"sh.{symbol}"
    else:
        return f"sz.{symbol}"


def fetch_example(symbol: str):
    bs_code = convert_symbol(symbol)

    print("正在登录 BaoStock...")
    lg = bs.login()
    if lg.error_code != "0":
        print("登录失败:", lg.error_msg)
        return

    print(f"开始拉取 {symbol} 日线数据...")

    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,open,high,low,close,volume,amount",
        start_date="2023-01-01",
        end_date=pd.Timestamp.today().strftime("%Y-%m-%d"),
        frequency="d",
        adjustflag="1",  # 后复权
    )

    if rs.error_code != "0":
        print("拉取失败:", rs.error_msg)
        bs.logout()
        return

    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())

    bs.logout()

    if not data_list:
        print("返回数据为空")
        return

    df = pd.DataFrame(data_list, columns=rs.fields)

    # 类型转换
    df["date"] = pd.to_datetime(df["date"])
    df[["open", "high", "low", "close", "volume", "amount"]] = \
        df[["open", "high", "low", "close", "volume", "amount"]].astype(float)

    print("\n===== 数据基本信息 =====")
    print("数据行数:", len(df))
    print("日期范围:", df["date"].min(), "->", df["date"].max())

    print("\n===== 前5行 =====")
    print(df.head())

    print("\n===== 后5行 =====")
    print(df.tail())

    print("\n测试完成 ✅")


if __name__ == "__main__":
    fetch_example("000001")   # 可改为其他股票测试
