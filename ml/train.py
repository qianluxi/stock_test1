"""
train.py

多股票 ML 信号训练（修正版）
- 输入：daily_prices + 技术指标
- 输出：
    1️⃣ 每只股票训练好的随机森林模型
    2️⃣ DataFrame 含 ml_signal（与原始 df 对齐，NaN 表示无法预测）
"""

import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import joblib

from db.database import SQLiteDB
from factors.indicators import add_all_indicators
from signals.signal_generator import generate_signals

DB_PATH = "stock.db"
MODEL_DIR = "ml/models"
os.makedirs(MODEL_DIR, exist_ok=True)

FEATURES = ["ma5", "ma10", "ma20", "rsi", "macd", "macd_signal", "macd_hist"]


def load_stock_data(symbol: str, db_path=DB_PATH) -> pd.DataFrame:
    db = SQLiteDB(db_path)
    db.connect()

    df = pd.read_sql(
        """
        SELECT trade_date, close_adj, open_adj, high_adj, low_adj, volume, amount
        FROM daily_prices
        WHERE symbol = ?
        ORDER BY trade_date
        """,
        db.conn,
        params=(symbol,)
    )

    df = add_all_indicators(df)
    df = generate_signals(df)  # 占位 signal 列
    return df


def prepare_ml_data(df: pd.DataFrame):
    df_ml = df.dropna(subset=FEATURES + ["close_adj"]).copy()
    if len(df_ml) < 50:
        return None, None, None  # 数据太少

    X = df_ml[FEATURES]
    y = (df_ml["close_adj"].shift(-1) > df_ml["close_adj"]).astype(int)
    X = X[:-1]
    y = y[:-1]
    df_ml = df_ml.iloc[:-1].copy()  # 对齐
    return X, y, df_ml


def train_stock(symbol: str):
    df = load_stock_data(symbol)
    X, y, df_pred = prepare_ml_data(df)
    if X is None:
        print(f"[{symbol}] 数据量太少，跳过训练")
        return None, None

    # 拆分训练/测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    # 训练模型
    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)
    accuracy = model.score(X_test, y_test)
    print(f"[{symbol}] 随机森林准确率: {accuracy:.4f}")

    # 生成预测信号，直接对齐原始 df_ml
    df_pred["ml_signal"] = model.predict(X)

    # 保存模型
    model_file = os.path.join(MODEL_DIR, f"{symbol}_rf.pkl")
    joblib.dump(model, model_file)
    print(f"[{symbol}] 模型已保存到 {model_file}")

    return model, df_pred


def train_multi_stocks(symbols: list):
    all_signals = {}
    for s in symbols:
        model, df_pred = train_stock(s)
        if df_pred is not None:
            all_signals[s] = df_pred
    return all_signals


if __name__ == "__main__":
    stock_pool = ["001229", "002264", "000881"]  # 可扩展
    all_signals = train_multi_stocks(stock_pool)

    # 输出最新 5 条信号，检查结果
    for symbol, df_signal in all_signals.items():
        print(f"\n[{symbol}] 最新 5 条 ML 信号：")
        print(df_signal[["trade_date", "close_adj", "ml_signal"]].tail())
