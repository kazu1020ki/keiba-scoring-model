# 競馬予想モデル/course/course_score.py
import argparse
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT_ROOT / "assets"

COURSE_WEIGHTS = {
    "東京": {"speed": 1.2, "lead": 0.7, "closing": 1.4},
    "中山": {"speed": 1.0, "lead": 1.3, "closing": 0.8},
    "京都": {"speed": 1.1, "lead": 0.9, "closing": 1.2},
    "阪神": {"speed": 1.1, "lead": 1.1, "closing": 1.0}
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--course", required=True)
    args = parser.parse_args()

    INPUT = ASSETS / f"race_{args.race_id}_{args.distance}m_scores.csv"
    OUTPUT = ASSETS / f"race_{args.race_id}_{args.distance}m_{args.course}_course.csv"

    df = pd.read_csv(INPUT)
    weights = COURSE_WEIGHTS[args.course]

    def calc(row):
        s, l, c = row["スピードスコア"], row["先行力スコア"], row["上がり力スコア"]
        if pd.isna(s) or pd.isna(l) or pd.isna(c):
            return None
        return round(
            s * weights["speed"] +
            l * weights["lead"] +
            c * weights["closing"], 2
        )

    col = f"{args.course}適性スコア"
    df[col] = df.apply(calc, axis=1)
    df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

    print(f"✅ 出力: {OUTPUT}")


if __name__ == "__main__":
    main()
