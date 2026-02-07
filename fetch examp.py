from data.fetch_daily import sync_daily_prices

stock_pool = ["001229", "002264", "000881"]
for s in stock_pool:
    sync_daily_prices(s)
