# signals/score_generator.py

import joblib
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier


# ==========================================================
# 模型路径
# ==========================================================

DEFAULT_MODEL_PATH = Path("ml/models/rf_global.pkl")


# ==========================================================
# 特征列（必须与训练一致）
# ==========================================================

FEATURE_COLUMNS = [
    "ma5", "ma10", "ma20",
    "rsi",
    "macd", "macd_signal", "macd_hist",
    "ret_1"
]


# ==========================================================
# ScoreGenerator
# ==========================================================

class ScoreGenerator:

    def __init__(
        self,
        model=None,
        model_path: Path = DEFAULT_MODEL_PATH
    ):
        """
        如果传入 model -> 使用该模型
        否则尝试从 model_path 加载
        """
        self.model_path = model_path

        if model is not None:
            self.model = model
        elif model_path.exists():
            self.model = joblib.load(model_path)
        else:
            self.model = None

    # ======================================================
    # 训练模型
    # ======================================================

    def fit(self, df_train: pd.DataFrame, save_model: bool = True):
        """
        在训练集上训练模型
        """

        self._validate_features(df_train)
        self._validate_label(df_train)

        X = df_train[FEATURE_COLUMNS]
        y = df_train["label"]

        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=6,
            random_state=42,
            n_jobs=-1
        )

        model.fit(X, y)

        self.model = model

        if save_model:
            self._save_model()

        return self

    # ======================================================
    # 预测
    # ======================================================

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        使用已训练模型生成 score
        """

        if self.model is None:
            raise ValueError("模型未训练或未加载")

        self._validate_features(df)

        X = df[FEATURE_COLUMNS]

        score = self.model.predict_proba(X)[:, 1]

        df_out = df.copy()
        df_out["score"] = score

        return df_out

    # ======================================================
    # 内部工具函数
    # ======================================================

    def _validate_features(self, df):
        missing = set(FEATURE_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"缺少特征列: {missing}")

    def _validate_label(self, df):
        if "label" not in df.columns:
            raise ValueError("缺少 label 列")

    def _save_model(self):
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, self.model_path)

    def load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")
        self.model = joblib.load(self.model_path)
        return self
