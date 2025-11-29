# 競馬予想モデル/predict/simple_rank.py
"""
コース適性スコア付きCSVを読み込んで、
スコア順に並べた簡易ランキングを表示するだけのプレースホルダ。
本格的な勝率・期待値モデルはここから拡張予定。
"""

from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
INPUT_CSV = ASSETS_DIR / "shutuba_with_scores_with_course.csv"
TARGET_COURSE = "東京"  # course_score.py と合わせる

def main():
    df = pd.read_csv(INPUT_CSV)
    col_name = f"{TARGET_COURSE}適性スコア"

    if col_name not in df.columns:
        raise ValueError(f"{col_name} 列が見つかりません。先に course/course_score.py を実行してください。")

    df_sorted = df.sort_values(col_name, ascending=False)

    print(f"=== {TARGET_COURSE}適性スコア順 ランキング ===")
    for _, row in df_sorted.iterrows():
        print(f"{row['馬名']:15s}  {col_name}: {row[col_name]}")

if __name__ == "__main__":
    main()
