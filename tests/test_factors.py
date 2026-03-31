from db.database import SQLiteDB
from factors.indicator_engine import IndicatorEngine
from factors.factor_writer import write_factors


db = SQLiteDB("db/stock.db")
db.connect()

df = db.load_data("2020-01-01","2024-12-31")

print("读取行情:", len(df))

engine = IndicatorEngine()

df = engine.compute_all(df)

write_factors(db, df)

db.close()

print("测试完成")