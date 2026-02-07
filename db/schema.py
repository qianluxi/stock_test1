"""
schema.py

SQLite 数据库表定义 + 索引
"""

ALL_SCHEMA_SQL = """
-- daily_prices 表：保存历史行情和基础指标
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol TEXT NOT NULL,                -- 股票/标的代码
    trade_date TEXT NOT NULL,            -- 交易日期（格式如：YYYY-MM-DD）
    open_adj REAL,                       -- 复权后开盘价
    high_adj REAL,                       -- 复权后最高价
    low_adj REAL,                        -- 复权后最低价
    close_adj REAL,                      -- 复权后收盘价
    volume REAL,                         -- 成交量
    amount REAL,                         -- 成交额
    ma5 REAL,                            -- 5日移动平均线
    ma10 REAL,                           -- 10日移动平均线
    ma20 REAL,                           -- 20日移动平均线
    rsi REAL,                            -- 相对强弱指数（默认常用14周期）
    macd REAL,                           -- MACD 主线
    macd_signal REAL,                    -- MACD 信号线
    macd_hist REAL,                      -- MACD 柱状线
    PRIMARY KEY (symbol, trade_date)     -- 复合主键：标的代码+交易日期，确保数据唯一
);

-- 技术指标索引，加快查询
CREATE INDEX IF NOT EXISTS idx_symbol_date ON daily_prices(symbol, trade_date);

-- 未来可扩展表：factors、财务指标等
-- CREATE TABLE IF NOT EXISTS factors (
--     symbol TEXT NOT NULL,
--     trade_date TEXT NOT NULL,
--     factor_name TEXT,
--     factor_value REAL,
--     PRIMARY KEY (symbol, trade_date, factor_name)
-- );
"""
