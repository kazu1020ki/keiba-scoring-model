# 競馬予想モデル/predict/simple_rank.py
import argparse
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT_ROOT / "assets"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--course", required=True)
    args = parser.parse_args()

    INPUT = ASSETS / f"race_{args.race_id}_{args.distance}m_{args.course}_course.csv"

    df = pd.read_csv(INPUT)
    col = f"{args.course}適性スコア"

    print(f"\n=== {args.course} 適性スコアランキング ===")
    df = df.sort_values(col, ascending=False)

    for _, r in df.iterrows():
        print(f"{r['馬名']:15s} {col}: {r[col]}")

    print("\n")


if __name__ == "__main__":
    main()
