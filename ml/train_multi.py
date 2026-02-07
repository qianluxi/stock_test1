# ml/train_multi.py

import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from features.build_features import build_features

MODEL_DIR = "ml/models"
os.makedirs(MODEL_DIR, exist_ok=True)


FEATURE_COLS = [
    "ma5", "ma10", "ma20",
    "rsi",
    "macd", "macd_signal", "macd_hist",
    "ret_1",
]


def build_market_dataset(stock_pool: list) -> pd.DataFrame:
    """拼接多股票训练集"""
    dfs = []
    for s in stock_pool:
        try:
            df = build_features(s)
            dfs.append(df)
        except Exception as e:
            print(f"[{s}] 跳过: {e}")

    df_all = pd.concat(dfs, ignore_index=True)
    return df_all


def time_split(df: pd.DataFrame, split_date: str):
    """按时间切分（防未来泄漏）"""
    train_df = df[df["trade_date"] < split_date]
    test_df = df[df["trade_date"] >= split_date]
    return train_df, test_df


def train_global_model(stock_pool: list, split_date="2025-01-01"):
    df_all = build_market_dataset(stock_pool)

    train_df, test_df = time_split(df_all, split_date)

    X_train = train_df[FEATURE_COLS]
    y_train = train_df["label"]

    X_test = test_df[FEATURE_COLS]
    y_test = test_df["label"]

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=50,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    acc = model.score(X_test, y_test)
    print(f"[GLOBAL] 验证集准确率: {acc:.4f}")

    model_path = os.path.join(MODEL_DIR, "rf_global.pkl")
    joblib.dump(model, model_path)
    print(f"[GLOBAL] 模型已保存: {model_path}")

    return model


if __name__ == "__main__":
    stock_pool = [
        "001229",
        "002264",
        "000881",
    ]

    train_global_model(stock_pool)
