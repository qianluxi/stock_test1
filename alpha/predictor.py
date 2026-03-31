import pandas as pd


class AlphaPredictor:

    def predict(self, trainer, X: pd.DataFrame, meta_df: pd.DataFrame):

        scores = trainer.predict(X)
        # ===== 实验：不用模型 =====
        #scores = X["ret_20_rank"]   # 或 ret_5_rank / momentum10_rank


        result = meta_df.copy()
        result["trade_date"] = pd.to_datetime(result["trade_date"])

        result["score_raw"] = scores

        # -----------------------------------
        # 1️⃣ 横截面标准化（已有）
        # -----------------------------------
        result["score"] = result.groupby("trade_date")["score_raw"] \
            .transform(lambda x: (x - x.mean()) / x.std() if x.std() != 0 else 0)

        return result

    # -----------------------------------
    # 🔥 新增：行业中性化
    # -----------------------------------
    def neutralize_by_industry(self, df: pd.DataFrame):

        df = df.copy()

        if "industry" not in df.columns:
            raise ValueError("缺少 industry 列，无法做行业中性化")

        # 行业内去均值
        df["score_neutral"] = df.groupby(
            ["trade_date", "industry"]
        )["score"].transform(lambda x: x - x.mean())

        return df