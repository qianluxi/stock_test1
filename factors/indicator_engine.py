import pandas as pd
import numpy as np


class IndicatorEngine:

    def compute_all(self, df):

        df = df.sort_values(["symbol", "trade_date"]).copy()

        df = self.add_returns(df)
        df = self.add_ma(df)
        df = self.add_rsi(df)
        df = self.add_macd(df)
        df = self.add_bollinger(df)
        df = self.add_atr(df)
        df = self.add_volume(df)
        df = self.add_volatility(df)

        df = self.add_roc(df)
        df = self.add_momentum(df)
        df = self.add_cci(df)
        df = self.add_williams_r(df)

        df = self.add_stat_features(df)

        return df


    def add_returns(self, df):

        g = df.groupby("symbol")["close_adj"]

        df["ret_1"] = g.pct_change(1)
        df["ret_5"] = g.pct_change(5)
        df["ret_20"] = g.pct_change(20)

        return df


    def add_ma(self, df):

        g = df.groupby("symbol")["close_adj"]

        for w in [5,10,20,60]:

            df[f"ma{w}"] = g.transform(lambda x: x.rolling(w).mean())

        return df


    def add_rsi(self, df, period=14):

        delta = df.groupby("symbol")["close_adj"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.groupby(df["symbol"]).transform(lambda x: x.rolling(period).mean())
        avg_loss = loss.groupby(df["symbol"]).transform(lambda x: x.rolling(period).mean())

        rs = avg_gain / avg_loss

        df["rsi14"] = 100 - (100 / (1 + rs))

        return df


    def add_macd(self, df):

        close = df.groupby("symbol")["close_adj"]

        ema12 = close.transform(lambda x: x.ewm(span=12).mean())
        ema26 = close.transform(lambda x: x.ewm(span=26).mean())

        macd = ema12 - ema26
        signal = macd.groupby(df["symbol"]).transform(lambda x: x.ewm(span=9).mean())

        df["macd"] = macd
        df["macd_signal"] = signal
        df["macd_hist"] = macd - signal

        return df


    def add_bollinger(self, df):

        close = df.groupby("symbol")["close_adj"]

        ma = close.transform(lambda x: x.rolling(20).mean())
        std = close.transform(lambda x: x.rolling(20).std())

        df["bb_mid"] = ma
        df["bb_upper"] = ma + 2 * std
        df["bb_lower"] = ma - 2 * std
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / ma

        return df


    def add_atr(self, df):

        prev_close = df.groupby("symbol")["close_adj"].shift(1)

        tr1 = df["high_adj"] - df["low_adj"]
        tr2 = (df["high_adj"] - prev_close).abs()
        tr3 = (df["low_adj"] - prev_close).abs()

        tr = pd.concat([tr1,tr2,tr3],axis=1).max(axis=1)

        df["tr"] = tr

        df["atr14"] = df.groupby("symbol")["tr"].transform(lambda x: x.rolling(14).mean())

        return df


    def add_volume(self, df):

        vol_ma5 = df.groupby("symbol")["volume"].transform(lambda x: x.rolling(5).mean())

        df["vol_ratio"] = df["volume"] / vol_ma5

        return df


    def add_volatility(self, df):

        df["volatility20"] = df.groupby("symbol")["ret_1"].transform(lambda x: x.rolling(20).std())

        return df


    def add_roc(self, df):

        df["roc12"] = df.groupby("symbol")["close_adj"].pct_change(12)

        return df


    def add_momentum(self, df):

        df["momentum10"] = df.groupby("symbol")["close_adj"].diff(10)

        return df


    def add_cci(self, df):

        tp = (df["high_adj"] + df["low_adj"] + df["close_adj"]) / 3

        ma = tp.groupby(df["symbol"]).transform(lambda x: x.rolling(20).mean())
        md = tp.groupby(df["symbol"]).transform(lambda x: x.rolling(20).apply(lambda y: np.mean(np.abs(y - y.mean()))))

        df["cci20"] = (tp - ma) / (0.015 * md)

        return df


    def add_williams_r(self, df):

        high14 = df.groupby("symbol")["high_adj"].transform(lambda x: x.rolling(14).max())
        low14 = df.groupby("symbol")["low_adj"].transform(lambda x: x.rolling(14).min())

        df["williams_r"] = -100 * (high14 - df["close_adj"]) / (high14 - low14)

        return df


    def add_stat_features(self, df):

        g = df.groupby("symbol")["ret_1"]

        df["skew20"] = g.transform(lambda x: x.rolling(20).skew())
        df["kurt20"] = g.transform(lambda x: x.rolling(20).kurt())

        return df