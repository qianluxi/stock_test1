import pandas as pd
import numpy as np


class FactorDiagnostics:

    # -----------------------------------
    # 1️⃣ 单因子IC
    # -----------------------------------
    def calc_factor_ic(self, df: pd.DataFrame, factor_cols: list):

        ic_dict = {}

        for col in factor_cols:
            ic_list = []

            for date, group in df.groupby("trade_date"):
                if group[col].std() == 0:
                    continue

                ic = group[col].corr(group["future_return"])
                if not np.isnan(ic):
                    ic_list.append(ic)

            ic_dict[col] = np.nanmean(ic_list)

        return pd.Series(ic_dict).sort_values(ascending=False)

    # -----------------------------------
    # 2️⃣ IC稳定性（IC_IR）
    # -----------------------------------
    def calc_ic_ir(self, df: pd.DataFrame, factor_cols: list):

        result = {}

        for col in factor_cols:
            ic_list = []

            for date, group in df.groupby("trade_date"):
                if group[col].std() == 0:
                    continue

                ic = group[col].corr(group["future_return"])
                if not np.isnan(ic):
                    ic_list.append(ic)

            ic_array = np.array(ic_list)

            if len(ic_array) > 0:
                result[col] = ic_array.mean() / ic_array.std() if ic_array.std() != 0 else 0
            else:
                result[col] = np.nan

        return pd.Series(result).sort_values(ascending=False)

    # -----------------------------------
    # 3️⃣ 因子分布检查
    # -----------------------------------
    def factor_stats(self, df: pd.DataFrame, factor_cols: list):

        stats = []

        for col in factor_cols:
            s = df[col]

            stats.append({
                "factor": col,
                "mean": s.mean(),
                "std": s.std(),
                "nan_ratio": s.isna().mean(),
                "zero_ratio": (s == 0).mean()
            })

        return pd.DataFrame(stats).sort_values("std")

    # -----------------------------------
    # 4️⃣ 因子相关性矩阵
    # -----------------------------------
    def factor_corr(self, df: pd.DataFrame, factor_cols: list):

        return df[factor_cols].corr()