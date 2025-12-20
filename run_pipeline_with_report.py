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
    csv_path = ASSETS / f"race_{race_id}_{distance}m_{course}_course.csv"
    df = pd.read_csv(csv_path)

    score_col = f"{course}適性スコア"
    df = df.dropna(subset=[score_col]).copy()
    df["モデル順位"] = df[score_col].rank(ascending=False, method="dense").astype(int)
    df = df.sort_values("モデル順位")

    # ★ 修正点：Path の結合は / を使う
    out_path = REPORT_DIR / f"report_{race_id}_{distance}m_{course}.txt"

    with out_path.open("w", encoding="utf-8") as f:
        f.write("==== 競馬予想レポート ====\n")
        f.write(f"レースID: {race_id}\n")
        f.write(f"距離: {distance}m\n")
        f.write(f"コース: {course}\n\n")
        f.write("--- モデル順位 ---\n")

        for _, row in df.iterrows():
            f.write(
                f"{row['モデル順位']}位 | {row['馬名']} | スコア: {round(row[score_col],3)}\n"
            )

    print(f"レポート生成: {out_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--course", required=True)
    parser.add_argument("--surface", required=True)
    parser.add_argument("--field_size", type=int, required=True)

    # ★ 当日バイアス（5段階）
    parser.add_argument("--bias_speed", type=int, default=0)
    parser.add_argument("--bias_lead", type=int, default=0)
    parser.add_argument("--bias_closing", type=int, default=0)

    # ★ スキップ機能
    parser.add_argument("--skip_crawl", action="store_true")
    parser.add_argument("--skip_score", action="store_true")

    args = parser.parse_args()

    # ------------------------------
    # 1. 出馬表クロール（必要なら）
    # ------------------------------
    if not args.skip_crawl:
        run(["python", "-m", "crawl.crawl_shutuba", "--race_id", args.race_id])
    else:
        print("🚫 crawl スキップ")

    # ------------------------------
    # 2. 過去5走スコア（必要なら）
    # ------------------------------
    if not args.skip_score:
        run([
            "python", "-m", "scoring.score_past5",
            "--race_id", args.race_id,
            "--distance", str(args.distance),
            "--field_size", str(args.field_size),
            "--surface", args.surface
        ])
    else:
        print("🚫 score_past5 スキップ")

    # ------------------------------
    # 3. コース適性スコア（バイアス付き）
    # ------------------------------
    run([
        "python", "-m", "course.course_score",
        "--race_id", args.race_id,
        "--distance", str(args.distance),
        "--course", args.course,
        "--surface", args.surface,
        "--bias_speed", str(args.bias_speed),
        "--bias_lead", str(args.bias_lead),
        "--bias_closing", str(args.bias_closing)
    ])

    # ------------------------------
    # 4. レポート生成
    # ------------------------------
    generate_report(args.race_id, args.distance, args.course)


if __name__ == "__main__":
    main()
