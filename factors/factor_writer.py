def write_factors(db, df):

    cols = [
        "symbol","trade_date",
        "ret_1","ret_5","ret_20",
        "ma5","ma10","ma20","ma60",
        "rsi14",
        "macd","macd_signal","macd_hist",
        "atr14",
        "bb_mid","bb_upper","bb_lower","bb_width",
        "vol_ratio",
        "volatility20",
        "roc12","momentum10","cci20","williams_r",
        "skew20","kurt20"
    ]

    df = df[cols].dropna()

    sql = """
    INSERT OR REPLACE INTO factor_values VALUES
    (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """

    data = [tuple(row) for row in df.values]

    db.executemany(sql, data)

    print("因子写入完成:", len(data))