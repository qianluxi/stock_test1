import pandas as pd
import numpy as np
import json
import os

from features.transforms import winsorize, zscore, zscore_industry, demean_industry
from features.cross_sectional import add_rank, add_rank_industry


class FeatureBuilder:

    def __init__(self):
        self.winsorize_limits = (0.01, 0.99)

        # 原始基础因子（用于生成派生特征）
        self.base_features = [
            "ret_1", "ret_5", "ret_20",
            "volatility20",
            "vol_ratio",
            "roc12", "momentum10",
            "rsi14",
            "macd", "macd_signal", "macd_hist",
            "cci20", "williams_r",
            "skew20", "kurt20",
            "atr14"
        ]

        # 新增非线性特征（不包含 vol_sq，它将在 rank 后单独生成）
        self.nonlinear_features = [
            "mom_x_vol",
            "ret20_x_skew",
            "ret5_abs",
            "momentum_sign"
        ]

        # 最终会处理的所有特征（原始 + 非线性）
        self.all_features = self.base_features + self.nonlinear_features

        self.drop_cols = [
            "open_adj", "high_adj", "low_adj", "close_adj",
            "volume", "tr"
        ]

        self.id_cols = ["symbol", "trade_date", "industry"]

    def build(self, df):
        df = df.copy()

        # 检查原始基础因子是否存在
        self._check_columns(df, self.base_features)

        # 筛选原始基础因子（确保后续派生只对这些列操作）
        df = self._select_base_features(df)

        # 生成非线性特征（不包含 vol_sq）
        df = self._add_nonlinear_features(df)

        # 按日期做横截面计算
        df = (
            df.groupby("trade_date", group_keys=False)
            .apply(self._build_cross_section)
        )

        df = self._drop_unused(df)
        self._save_feature_list(df)
        return df

    def _build_cross_section(self, df):
        # 1. 去极值
        df = winsorize(df, self.all_features, *self.winsorize_limits)

        if "industry" in df.columns:
            df["industry"] = df["industry"].fillna("UNKNOWN")

        # 2. 行业内去均值（可选）
        df = demean_industry(df, self.all_features)

        # 3. 添加排名（全市场 + 行业内）
        df = add_rank(df, self.all_features)
        df = add_rank_industry(df, self.all_features)

        # 4. 生成 vol_sq（依赖 volatility20_rank）
        if "volatility20_rank" in df.columns:
            df["vol_sq"] = df["volatility20_rank"] ** 2
        elif "volatility20" in df.columns:
            df["vol_sq"] = df["volatility20"] ** 2
            print("[WARNING] volatility20_rank 不存在，vol_sq 使用 volatility20^2")
        else:
            df["vol_sq"] = np.nan

        # 5. 添加 zscore（全市场 + 行业内），vol_sq 单独加入列表
        features_with_vol_sq = self.all_features + ["vol_sq"]
        df = zscore(df, features_with_vol_sq)
        df = zscore_industry(df, features_with_vol_sq)

        return df

    def _check_columns(self, df, feature_list):
        """只检查原始基础因子是否存在"""
        missing = [col for col in feature_list if col not in df.columns]
        if missing:
            print(f"[WARNING] 缺少基础因子列: {missing}")

    def _select_base_features(self, df):
        """只保留原始基础因子（非线性特征还未生成）"""
        cols = self.id_cols + self.base_features
        cols = [col for col in cols if col in df.columns]
        return df[cols]

    def _add_nonlinear_features(self, df):
        """添加非线性组合特征（vol_sq 除外）"""
        df = df.copy()

        # mom_x_vol
        if "momentum10" in df.columns and "volatility20" in df.columns:
            df["mom_x_vol"] = df["momentum10"] * df["volatility20"]
        else:
            df["mom_x_vol"] = np.nan

        # ret20_x_skew
        if "ret_20" in df.columns and "skew20" in df.columns:
            df["ret20_x_skew"] = df["ret_20"] * df["skew20"]
        else:
            df["ret20_x_skew"] = np.nan

        # ret5_abs
        if "ret_5" in df.columns:
            df["ret5_abs"] = df["ret_5"].abs()
        else:
            df["ret5_abs"] = np.nan

        # momentum_sign
        if "momentum10" in df.columns:
            df["momentum_sign"] = np.sign(df["momentum10"])
        else:
            df["momentum_sign"] = np.nan

        return df

    def _drop_unused(self, df):
        drop_cols = [col for col in self.drop_cols if col in df.columns]
        return df.drop(columns=drop_cols, errors="ignore")

    def _save_feature_list(self, df):
        feature_cols = [col for col in df.columns if col not in self.id_cols]
        os.makedirs("features/registry", exist_ok=True)
        with open("features/registry/features_v1.json", "w") as f:
            json.dump(feature_cols, f, indent=2)