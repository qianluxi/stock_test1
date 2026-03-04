import pandas as pd


class LabelEngine:
    """
    负责生成未来收益标签
    """

    def add_future_return(self, df: pd.DataFrame, horizon: int = 5):

        df = df.sort_values(["symbol", "trade_date"])

        df["future_return"] = (
            df.groupby("symbol")["close_adj"]
            .shift(-horizon) / df["close_adj"] - 1
        )

        return df