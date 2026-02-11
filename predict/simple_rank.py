# 競馬予想モデル/predict/simple_rank.py
import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT_ROOT / "assets"


def resolve_input_path(race_id: str, course: str, distance: int, surface: str | None) -> Path:
    """
    現行命名規則の course_scores.csv を解決する。
    surface 指定があれば完全一致、未指定なら候補1件を探索。
    """
    if surface:
        path = ASSETS / (
            f"race_{race_id}_{course}_{surface}{distance}m_course_scores.csv"
        )
        if not path.exists():
            raise FileNotFoundError(f"入力CSVが存在しません: {path}")
        return path

    candidates = sorted(
        ASSETS.glob(f"race_{race_id}_{course}_*{distance}m_course_scores.csv")
    )
    if not candidates:
        raise FileNotFoundError(
            f"入力CSVが見つかりません: race_id={race_id}, course={course}, distance={distance}"
        )
    if len(candidates) > 1:
        raise RuntimeError(
            "候補が複数あります。--surface を指定してください: "
            + ", ".join(p.name for p in candidates)
        )
    return candidates[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--course", required=True)
    parser.add_argument("--surface", choices=["芝", "ダ"], default=None)
    args = parser.parse_args()

    input_path = resolve_input_path(
        race_id=args.race_id,
        course=args.course,
        distance=args.distance,
        surface=args.surface,
    )

    import pandas as pd

    df = pd.read_csv(input_path)
    col = f"{args.course}適性スコア"

    print(f"\n=== {args.course} 適性スコアランキング ===")
    df = df.sort_values(col, ascending=False)

    for _, r in df.iterrows():
        print(f"{r['馬名']:15s} {col}: {r[col]}")

    print("\n")


if __name__ == "__main__":
    main()
