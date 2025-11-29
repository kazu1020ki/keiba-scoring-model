# evaluation/evaluate_batch.py

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT_ROOT / "assets"


def run_command(cmd):
    """サブプロセスでコマンド実行（エラーも表示）"""
    print(f"\n▶ 実行中: {cmd}\n")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ エラー発生: {cmd}")
    else:
        print(f"✅ 完了: {cmd}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_list", required=True, help="スペース区切りのレース一覧ファイル")
    args = parser.parse_args()

    race_list_path = Path(args.race_list)
    if not race_list_path.exists():
        raise FileNotFoundError(f"レースリストが見つかりません: {race_list_path}")

    print(f"📘 レース一覧を読み込み: {race_list_path}")

    with race_list_path.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    for line in lines:
        # フォーマット: race_id distance course
        parts = line.split()
        if len(parts) != 3:
            print(f"⚠ フォーマット不正のためスキップ: {line}")
            continue

        race_id, distance, course = parts
        distance = int(distance)

        print("\n========================================")
        print(f"🏇 レース実行: {race_id}（{distance}m / {course}）")
        print("========================================")

        # 1. crawl
        run_command(
            f"python -m crawl.crawl_shutuba --race_id {race_id}"
        )

        # 2. scoring
        run_command(
            f"python -m scoring.score_past5 --race_id {race_id} --distance {distance}"
        )

        # 3. course
        run_command(
            f"python -m course.course_score --race_id {race_id} --distance {distance} --course {course}"
        )

        # 4. evaluation（単レース版）
        run_command(
            f"python -m evaluation.evaluate_single_race --race_id {race_id} --distance {distance} --course {course}"
        )

    print("\n========================================")
    print("🎉 全レースの評価が完了しました!")
    print("========================================\n")


if __name__ == "__main__":
    main()
