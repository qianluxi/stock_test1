"""
signal_generator.py

信号生成模块占位
- 输入：带指标的 DataFrame
- 输出：买卖信号或 label
"""

import pandas as pd

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    生成买卖信号（placeholder）

    参数:
        df: DataFrame, 已经包含技术指标列
    
    返回:
        df: DataFrame, 新增 'signal' 列（暂时全为 0）
    """
    df = df.copy()
    df["signal"] = 0  # 暂时全部置 0
    return df
