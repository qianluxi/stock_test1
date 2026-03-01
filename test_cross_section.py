from ml.dataset import build_market_dataset
from signals.score_generator import ScoreGenerator
from signals.cross_section import CrossSection
from stock_pool import STOCK_POOL


# ===============================
# Step 1: 构建特征 + 生成 score
# ===============================

print("构建特征数据...")
df_features = build_market_dataset(STOCK_POOL)

print("生成 score...")
sg = ScoreGenerator()
df_with_score = sg.generate_score(df_features)

print("样本总数:", len(df_with_score))
print("股票数量:", df_with_score["symbol"].nunique())


# ===============================
# Step 2: 横截面分组
# ===============================

cs = CrossSection(n_groups=5)  # 先不用市值加权
df_cs = cs.rank_and_group(df_with_score)

print("\n横截面构建完成")
print(df_cs.head())


# ===============================
# Step 3: 随机抽一天检查
# ===============================
# 1. 手动指定想要抽样的日期
sample_date = "2026-01-29"
print(f"\n抽样日期: {sample_date}")

df_day = df_cs[df_cs["trade_date"] == sample_date].copy()
df_day = df_day.sort_values("rank")

print("\n当天前10名:")
print(df_day[["symbol", "score", "rank", "group"]].head(10))

print("\n当天最后10名:")
print(df_day[["symbol", "score", "rank", "group"]].tail(10))


# ===============================
# Step 4: 检查分组是否均匀
# ===============================

print("\n分组数量分布:")
print(df_day["group"].value_counts().sort_index())
