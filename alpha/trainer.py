import joblib
import lightgbm as lgb
import pandas as pd
import os


class AlphaTrainer:

    def __init__(self):

        self.model = lgb.LGBMRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )

        self.feature_names = None

    # ------------------------------
    # 训练
    # ------------------------------
    def fit(self, X: pd.DataFrame, y: pd.Series):

        # ✅ 保存特征名（关键）
        self.feature_names = list(X.columns)

        # ✅ LightGBM 可直接处理 NaN（不强制 drop）
        self.model.fit(X, y)

    # ------------------------------
    # 预测
    # ------------------------------
    def predict(self, X: pd.DataFrame):

        # ✅ 保证列顺序一致（非常关键）
        if self.feature_names is not None:
            X = X[self.feature_names]

        return self.model.predict(X)

    # ------------------------------
    # 保存模型
    # ------------------------------
    def save(self, path: str):

        os.makedirs(os.path.dirname(path), exist_ok=True)

        joblib.dump({
            "model": self.model,
            "feature_names": self.feature_names
        }, path)

    # ------------------------------
    # 加载模型
    # ------------------------------
    def load(self, path: str):

        data = joblib.load(path)

        self.model = data["model"]
        self.feature_names = data["feature_names"]