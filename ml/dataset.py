# ml/dataset.py

import pandas as pd
from features.build_features import build_features


def build_market_dataset(stock_pool: list) -> pd.DataFrame:
    """
    构建多股票拼接的 ML 数据集
    """
    dfs = []

    for symbol in stock_pool:
        try:
            df = build_features(symbol)
            df["symbol"] = symbol  # 防御性：确保存在
            dfs.append(df)
        except Exception as e:
            print(f"[{symbol}] 跳过: {e}")

    if not dfs:
        raise RuntimeError("未构建任何有效股票数据")

    df_all = pd.concat(dfs, ignore_index=True)
    return df_all
