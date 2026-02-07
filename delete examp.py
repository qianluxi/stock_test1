from db.cleanup import delete_stock, delete_stock_date_range

# 删除整个股票
delete_stock("600519")

# 删除指定日期段
#delete_stock_date_range("600519", "2025-01-01", "2025-12-31")
