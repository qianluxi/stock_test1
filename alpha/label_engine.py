import pandas as pd


class LabelEngine:
    """
    负责生成未来收益标签
    """

    def add_future_return(self, df: pd.DataFrame, horizon: int = 5):

        df = df.copy()

        # ✅ 时间统一
        df["trade_date"] = pd.to_datetime(df["trade_date"])

        # ✅ 排序（保证 shift 正确）
        df = df.sort_values(["symbol", "trade_date"])

        # ✅ 避免除零
        df = df[df["close_adj"] > 0]

        # ✅ 未来收益
        df["future_return"] = (
            df.groupby("symbol")["close_adj"]
            .shift(-horizon) / df["close_adj"] - 1
        )

        return df