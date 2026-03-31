# factors/factor_writer.py
def write_factors(db, df):

    if df is None or df.empty:
        print("Factor为空，无写入")
        return

    # ---------------------------
    # 1️⃣ 获取表结构（只写合法列）
    # ---------------------------
    cursor = db.conn.cursor()
    cursor.execute("PRAGMA table_info(factor_values)")
    table_info = cursor.fetchall()

    table_cols = [col[1] for col in table_info]

    # ---------------------------
    # 2️⃣ 过滤字段（关键修复）
    # ---------------------------
    df = df[[col for col in df.columns if col in table_cols]]

    # ---------------------------
    # 3️⃣ 必要字段
    # ---------------------------
    required = ["symbol", "trade_date"]
    df = df.dropna(subset=required)

    if df.empty:
        print("Factor为空（过滤后），无写入")
        return

    # ---------------------------
    # 4️⃣ 排序 + 去重
    # ---------------------------
    df = df.sort_values(["trade_date", "symbol"])
    df = df.drop_duplicates(subset=["symbol", "trade_date"])

    # ---------------------------
    # 5️⃣ 删除旧数据（幂等）
    # ---------------------------
    min_date = df["trade_date"].min()
    max_date = df["trade_date"].max()

    db.conn.execute(f"""
        DELETE FROM factor_values
        WHERE trade_date BETWEEN '{min_date}' AND '{max_date}'
    """)
    db.conn.commit()

    # ---------------------------
    # 6️⃣ 写入
    # ---------------------------
    df.to_sql(
        "factor_values",
        db.conn,
        if_exists="append",
        index=False
    )

    print(f"Factor写入完成: {len(df)} 行")