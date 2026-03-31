def write_features(db, df):
    """
    将 Feature DataFrame 写入 feature_values 表

    关键设计：
    - 不做全量 dropna
    - 只保证主键存在
    - 自动对齐数据库 schema
    - 避免重复写入（先删后插）
    """

    if df is None or df.empty:
        print("Feature为空，无写入")
        return

    # ---------------------------
    # 1️⃣ 去掉不入库字段
    # ---------------------------
    if "industry" in df.columns:
        df = df.drop(columns=["industry"])

    # ---------------------------
    # 2️⃣ 必须字段校验
    # ---------------------------
    required_cols = ["symbol", "trade_date"]

    df = df.dropna(subset=required_cols)

    if df.empty:
        print("Feature为空（主键缺失后），无写入")
        return

    # ---------------------------
    # 3️⃣ 获取数据库表结构（schema对齐）
    # ---------------------------
    cursor = db.conn.cursor()
    cursor.execute("PRAGMA table_info(feature_values)")
    table_info = cursor.fetchall()

    table_cols = [col[1] for col in table_info]

    # 保留数据库存在的列
    df = df[[col for col in df.columns if col in table_cols]]

    # ---------------------------
    # 4️⃣ 排序（保证稳定性）
    # ---------------------------
    df = df.sort_values(["trade_date", "symbol"]).reset_index(drop=True)

    # ---------------------------
    # 5️⃣ 去重（防止重复写入）
    # ---------------------------
    df = df.drop_duplicates(subset=["symbol", "trade_date"])

    # ---------------------------
    # 6️⃣ 删除已有数据（幂等写入）
    # ---------------------------
    # 提取日期范围（优化性能）
    min_date = df["trade_date"].min()
    max_date = df["trade_date"].max()

    delete_sql = f"""
    DELETE FROM feature_values
    WHERE trade_date BETWEEN '{min_date}' AND '{max_date}'
    """

    db.conn.execute(delete_sql)
    db.conn.commit()

    # ---------------------------
    # 7️⃣ 写入数据库
    # ---------------------------
    df.to_sql(
        "feature_values",
        db.conn,
        if_exists="append",
        index=False
    )

    print(f"Feature写入完成: {len(df)} 行")