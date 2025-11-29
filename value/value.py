import pandas as pd

# ===== 設定 =====
INPUT_CSV = "shutuba_with_scores.csv"
OUTPUT_CSV = "shutuba_with_scores_with_course.csv"

TARGET_COURSE = "京都"

COURSE_WEIGHTS = {
    "東京": {"speed": 1.2, "lead": 0.7, "closing": 1.4},
    "中山": {"speed": 1.0, "lead": 1.3, "closing": 0.8},
    "京都": {"speed": 1.1, "lead": 0.9, "closing": 1.2},
    "阪神": {"speed": 1.1, "lead": 1.1, "closing": 1.0}
}

# ===== 読み込み =====
df = pd.read_csv(INPUT_CSV)

weights = COURSE_WEIGHTS[TARGET_COURSE]

# ===== コース評価スコア算出 =====
def calc_course_score(row):
    speed = row["スピードスコア"]
    lead = row["先行力スコア"]
    closing = row["上がり力スコア"]

    if pd.isna(speed) or pd.isna(lead) or pd.isna(closing):
        return None

    score = (
        speed * weights["speed"]
        + lead * weights["lead"]
        + closing * weights["closing"]
    )
    return round(score, 2)

df["東京適性スコア"] = df.apply(calc_course_score, axis=1)

# ===== 出力 =====
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print("✅ 東京用コース適性スコア付与完了:", OUTPUT_CSV)
