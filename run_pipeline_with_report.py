import argparse
import subprocess
from pathlib import Path
import pandas as pd

from preprocess.race_filename import (
    parse_race_meta_from_filename,
    STAGE_RAW,
)

PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS = PROJECT_ROOT / "assets"
REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_DIR.mkdir(exist_ok=True)


# ==============================
# helpers
# ==============================
def run(cmd: list):
    print("実行:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def find_raw_csv_by_race_id(race_id: str) -> Path | None:
    """
    assets 配下から race_id に一致する raw.csv を1件探す
    """
    candidates = list(ASSETS.glob(f"race_{race_id}_*_raw.csv"))
    if not candidates:
        return None
    if len(candidates) > 1:
        raise RuntimeError(f"raw.csv が複数見つかりました: {candidates}")
    return candidates[0]


def generate_report(meta: dict):
    """
    course_scores.csv を読み、最終レポートを生成
    """
    race_id = meta["race_id"]
    course = meta["course"]
    surface = meta["surface"]
    distance = meta["distance"]

    csv_path = ASSETS / (
        f"race_{race_id}_{course}_{surface}{distance}m_course_scores.csv"
    )
    df = pd.read_csv(csv_path)

    score_col = f"{course}適性スコア"
    df = df.dropna(subset=[score_col]).copy()
    df["モデル順位"] = df[score_col].rank(
        ascending=False, method="dense"
    ).astype(int)
    df = df.sort_values("モデル順位")

    race_no = int(race_id[-2:])

    out_path = REPORT_DIR / (
        f"report_{race_no:02d}R_"
        f"{course}_{surface}{distance}m_"
        f"{race_id}.txt"
    )

    with out_path.open("w", encoding="utf-8") as f:
        f.write("==== 競馬予想レポート ====\n")
        f.write(f"レースID: {race_id}\n")
        f.write(f"コース: {course}\n")
        f.write(f"距離: {surface}{distance}m\n\n")
        f.write("--- モデル順位 ---\n")

        for _, row in df.iterrows():
            f.write(
                f"{row['モデル順位']}位 | {row['馬名']} | "
                f"スコア: {round(row[score_col], 3)}\n"
            )

    print(f"レポート生成: {out_path}")


# ==============================
# main
# ==============================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)

    # ★ 当日バイアス（任意 override）
    parser.add_argument("--bias_speed", type=int, default=0)
    parser.add_argument("--bias_lead", type=int, default=0)
    parser.add_argument("--bias_closing", type=int, default=0)

    args = parser.parse_args()

    # ------------------------------
    # 1. raw.csv 探索
    # ------------------------------
    raw_csv = find_raw_csv_by_race_id(args.race_id)

    if raw_csv:
        print(f"📦 既存 raw.csv を使用: {raw_csv.name}")
    else:
        print("📡 raw.csv が無いため crawl 実行")
        run([
            "python", "-m", "crawl.crawl_shutuba",
            "--race_id", args.race_id
        ])
        raw_csv = find_raw_csv_by_race_id(args.race_id)
        if not raw_csv:
            raise RuntimeError("crawl 後も raw.csv が見つかりません")

    # ------------------------------
    # 2. filename → meta
    # ------------------------------
    meta = parse_race_meta_from_filename(raw_csv.name)
    if meta["stage"] != STAGE_RAW:
        raise RuntimeError("raw.csv ではありません")

    race_id = meta["race_id"]
    course = meta["course"]
    surface = meta["surface"]
    distance = meta["distance"]
    field_size = meta["field_size"]

    print(f"🧠 レース条件: {course} {surface}{distance}m / {field_size}頭")

    # ------------------------------
    # 3. 過去5走スコア
    # ------------------------------
    run([
        "python", "-m", "scoring.score_past5",
        "--race_id", race_id,
        "--input_csv", str(raw_csv),
    ])

    # ------------------------------
    # 4. コース適性スコア（バイアス付き）
    # ------------------------------
    run([
        "python", "-m", "course.course_score",
        "--race_id", race_id,
        "--course", course,
        "--surface", surface,
        "--distance", str(distance),
        "--bias_speed", str(args.bias_speed),
        "--bias_lead", str(args.bias_lead),
        "--bias_closing", str(args.bias_closing),
    ])

    # ------------------------------
    # 5. レポート生成
    # ------------------------------
    generate_report(meta)

    # ------------------------------
    # 6. 期待値レポート生成（単勝/ワイド）
    # ------------------------------
    run([
        "python", "-m", "predict.ev_report",
        "--race_id", race_id,
    ])


if __name__ == "__main__":
    main()
