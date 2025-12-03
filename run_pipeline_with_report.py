# run_pipeline_with_report.py（新仕様対応版）
import argparse
import subprocess
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS = PROJECT_ROOT / "assets"
REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_DIR.mkdir(exist_ok=True)


def run(cmd: list):
    print("実行:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def generate_report(race_id, distance, course):
    """course スコア CSV から簡易レポート生成"""
    csv_path = ASSETS / f"race_{race_id}_{distance}m_{course}_course.csv"
    df = pd.read_csv(csv_path)

    score_col = f"{course}適性スコア"
    df = df.dropna(subset=[score_col]).copy()
    df["モデル順位"] = df[score_col].rank(ascending=False, method="dense").astype(int)
    df = df.sort_values("モデル順位")

    out_path = REPORT_DIR / f"report_{race_id}_{distance}m_{course}.txt"

    with out_path.open("w", encoding="utf-8") as f:
        f.write("==== 競馬予想レポート ====\n")
        f.write(f"レースID: {race_id}\n")
        f.write(f"距離: {distance}m\n")
        f.write(f"コース: {course}\n\n")
        f.write("--- モデル順位 ---\n")

        for _, row in df.iterrows():
            f.write(
                f"{row['モデル順位']}位 | "
                f"{row['馬名']} | "
                f"スコア: {round(row[score_col],3)}\n"
            )

    print(f"レポート生成: {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--course", required=True)      # 東京 / 中山 / …
    parser.add_argument("--surface", required=True)     # 芝 / ダ
    parser.add_argument("--field_size", type=int, required=True)

    args = parser.parse_args()

    # ------------------------------
    # 1. 出馬表クロール（必要なら）
    # ------------------------------
    run(["python", "-m", "crawl.crawl_shutuba", "--race_id", args.race_id])

    # ------------------------------
    # 2. 過去5走スコア（score_past5） 新仕様
    # ------------------------------
    run([
        "python", "-m", "scoring.score_past5",
        "--race_id", args.race_id,
        "--distance", str(args.distance),
        "--field_size", str(args.field_size),
        "--surface", args.surface
    ])

    # ------------------------------
    # 3. コース適性スコア（course_score） 新仕様
    # ------------------------------
    run([
        "python", "-m", "course.course_score",
        "--race_id", args.race_id,
        "--distance", str(args.distance),
        "--course", args.course,
        "--surface", args.surface
    ])

    # ------------------------------
    # 4. レポート生成
    # ------------------------------
    generate_report(args.race_id, args.distance, args.course)


if __name__ == "__main__":
    main()
