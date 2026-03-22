import pandas as pd


class AlphaPredictor:

    def predict(self, trainer, X: pd.DataFrame, meta_df: pd.DataFrame):

        # -----------------------------
        # 1️⃣ 使用 trainer 预测（保证特征对齐）
        # -----------------------------
        scores = trainer.predict(X)

        # -----------------------------
        # 2️⃣ 组装结果
        # -----------------------------
        result = meta_df.copy()

        result["trade_date"] = pd.to_datetime(result["trade_date"])

        result["score_raw"] = scores  # 原始分数（保留调试用）

        # -----------------------------
        # 3️⃣ 横截面标准化（关键）
        # -----------------------------
        result["score"] = result.groupby("trade_date")["score_raw"] \
            .transform(
                lambda x: (x - x.mean()) / x.std()
                if x.std() != 0 else 0
            )

        # -----------------------------
        # 4️⃣ 输出
        # -----------------------------
        return result[[
            "trade_date",
            "symbol",
            "score",
            "future_return"
        ]]