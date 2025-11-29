# 競馬予想モデル/course/course_score.py
"""
assets/shutuba_with_scores.csv を読み込み、
コース別の重み付けによる適性スコアを付与して
assets/shutuba_with_scores_with_course.csv に出力するスクリプト
"""

import pandas as pd
from pathlib import Path

# ===== パス設定 =====
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
ASSETS_DIR.mkdir(exist_ok=True)

INPUT_CSV = ASSETS_DIR / "shutuba_with_scores.csv"
OUTPUT_CSV = ASSETS_DIR / "shutuba_with_scores_with_course.csv"

# ===== 設定 =====
TARGET_COURSE = "東京"

COURSE_WEIGHTS = {
    "東京": {"speed": 1.2, "lead": 0.7, "closing": 1.4},
    "中山": {"speed": 1.0, "lead": 1.3, "closing": 0.8},
    "京都": {"speed": 1.1, "lead": 0.9, "closing": 1.2},
    "阪神": {"speed": 1.1, "lead": 1.1, "closing": 1.0}
}


def main():
    df = pd.read_csv(INPUT_CSV)

    if TARGET_COURSE not in COURSE_WEIGHTS:
        raise ValueError(f"TARGET_COURSE={TARGET_COURSE} は COURSE_WEIGHTS に定義されていません。")

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

    col_name = f"{TARGET_COURSE}適性スコア"
    df[col_name] = df.apply(calc_course_score, axis=1)

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"✅ {TARGET_COURSE}用コース適性スコア付与完了: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
