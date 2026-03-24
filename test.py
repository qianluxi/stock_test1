import tushare as ts
import pandas as pd

ts.set_token("15dac6dbcb4ba1afb3d380cfdd6d2dcc3dc77d99e9d484fbce054b75")
pro = ts.pro_api()

# 获取数据
df = pro.query("stock_basic", limit=5)

# 调试信息：看看df的类型、形状和内容
print(f"df的类型是: {type(df)}")
print(f"df的形状是 (行, 列): {df.shape}")
print(f"df的列名是: {df.columns.tolist()}")

# 如果df不是空的，但打印不出来，可以试试直接查看所有数据
if not df.empty:
    print("数据内容如下:")
    print(df.to_string())  # 强制打印所有内容
else:
    print("df确实是空的 (empty)")

# 尝试获取2024年1月的交易日历，这个接口门槛低，便于测试
df_cal = pro.trade_cal(start_date='20240101', end_date='20240131')
print(df_cal.head())