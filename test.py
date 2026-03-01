from db.database import SQLiteDB
import pandas as pd
db = SQLiteDB("stock.db")
db.connect()

df = pd.read_sql("""
SELECT DISTINCT symbol
FROM daily_prices
ORDER BY symbol
""", db.conn)

print(df.head(20))
db.close()
