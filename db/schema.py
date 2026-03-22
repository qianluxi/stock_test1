"""
数据库表结构
"""

# 股票基本信息
STOCK_BASIC_SQL = """
CREATE TABLE IF NOT EXISTS stock_basic (
    ts_code TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    area TEXT,
    industry TEXT,
    list_date TEXT NOT NULL
);
"""

# 市值信息
DAILY_BASIC_SQL = """
CREATE TABLE IF NOT EXISTS daily_basic (
    ts_code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    total_mv REAL,
    circ_mv REAL,
    PRIMARY KEY (ts_code, trade_date)
);
"""

# 日线行情
DAILY_PRICES_SQL = """
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open_adj REAL,
    high_adj REAL,
    low_adj REAL,
    close_adj REAL,
    volume REAL,
    amount REAL,
    PRIMARY KEY (symbol, trade_date)
);
"""

# 同步日志
SYNC_LOG_SQL = """
CREATE TABLE IF NOT EXISTS sync_log (
    symbol TEXT PRIMARY KEY,
    last_sync_date TEXT NOT NULL,
    row_count INTEGER,
    updated_at TEXT NOT NULL
);
"""

# 因子计算
FACTOR_VALUES_SQL = """
CREATE TABLE IF NOT EXISTS factor_values (
    symbol TEXT NOT NULL,
    trade_date TEXT NOT NULL,

    ret_1 REAL,
    ret_5 REAL,
    ret_20 REAL,

    ma5 REAL,
    ma10 REAL,
    ma20 REAL,
    ma60 REAL,

    rsi14 REAL,

    macd REAL,
    macd_signal REAL,
    macd_hist REAL,

    atr14 REAL,

    bb_mid REAL,
    bb_upper REAL,
    bb_lower REAL,
    bb_width REAL,

    vol_ratio REAL,

    volatility20 REAL,

    roc12 REAL,
    momentum10 REAL,
    cci20 REAL,
    williams_r REAL,

    skew20 REAL,
    kurt20 REAL,

    PRIMARY KEY(symbol, trade_date)
);
"""

# 汇总（database.py 会调用）
ALL_SCHEMA_SQL = [
    STOCK_BASIC_SQL,
    DAILY_BASIC_SQL,
    DAILY_PRICES_SQL,
    SYNC_LOG_SQL,
    FACTOR_VALUES_SQL
]
