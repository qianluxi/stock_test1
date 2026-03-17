import pandas as pd


class AlphaPredictor:

    def predict(self, model, X, meta_df: pd.DataFrame):

        scores = model.predict(X)

        result = meta_df.copy()
        result["score"] = scores

        return result[[
            "trade_date",
            "symbol",
            "score",
            "future_return"
        ]]