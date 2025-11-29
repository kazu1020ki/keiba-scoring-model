# 競馬予想モデル/scoring/score_past5.py
"""
assets/shutuba_with_past5.csv を読み込み、
各馬のスピード・上がり力・先行力スコアを算出して
assets/shutuba_with_scores.csv に出力するスクリプト
"""

import numpy as np
import pandas as pd
from pathlib import Path

from preprocess.utils import (
    parse_distance,
    time_to_seconds,
    convert_distance_time,
    parse_position,
)

# ==============================
# ▼ 手動設定
# ==============================
TARGET_DIST = 1600   # ← ここを予想レースの距離に変更する（例: 1200, 1800など）
FIELD_SIZE = 16      # 想定フルゲート（通過順位の割合計算用）

# ペース補正（上がり評価用）
PACE_CORRECTION_CLOSING = {
    "ハイ": -8,
    "ミドル": 0,
    "スロー": 8
}

# ペース補正（先行力評価用）
PACE_CORRECTION_LEAD = {
    "ハイ": 10,
    "ミドル": 0,
    "スロー": -10
}

# ==============================
# ▼ パス設定
# ==============================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
ASSETS_DIR.mkdir(exist_ok=True)

INPUT_CSV = ASSETS_DIR / "shutuba_with_past5.csv"
OUTPUT_CSV = ASSETS_DIR / "shutuba_with_scores.csv"


def main():
    # ==============================
    # ▼ 読み込み
    # ==============================
    df = pd.read_csv(INPUT_CSV)

    speed_scores = []
    closing_scores = []
    lead_scores = []

    for _, row in df.iterrows():

        speeds = []
        closings = []
        leads = []

        for n in range(1, 5 + 1):
            dist_raw = row.get(f"{n}走前_距離")
            time_raw = row.get(f"{n}走前_タイム")
            agari = row.get(f"{n}走前_上り")
            pace = row.get(f"{n}走前_ペース")
            passage = row.get(f"{n}走前_通過")

            dist = parse_distance(dist_raw)
            time_sec = time_to_seconds(time_raw)

            if dist is None or time_sec is None:
                continue

            # ========= スピード評価 =========
            adjusted_time = convert_distance_time(time_sec, dist, TARGET_DIST)
            if adjusted_time is not None:
                speeds.append(adjusted_time)

            # ========= 上がり力評価 =========
            if not pd.isna(agari):
                agari_val = float(agari)
                base = 60 - agari_val   # 上がりが速いほど高評価
                base += PACE_CORRECTION_CLOSING.get(pace, 0)
                closings.append(base)

            # ========= 先行力評価 =========
            pos_val = parse_position(passage, field_size=FIELD_SIZE)
            if pos_val is not None:
                lead = pos_val * 100 + PACE_CORRECTION_LEAD.get(pace, 0)
                leads.append(lead)

        # ========= 各スコア生成 =========
        speed_score = round(200 - np.mean(speeds), 2) if speeds else None
        closing_score = round(np.mean(closings), 2) if closings else None
        lead_score = round(np.mean(leads), 2) if leads else None

        speed_scores.append(speed_score)
        closing_scores.append(closing_score)
        lead_scores.append(lead_score)

    # ==============================
    # ▼ 出力
    # ==============================
    result = pd.DataFrame({
        "馬名": df["馬名"],
        "スピードスコア": speed_scores,
        "上がり力スコア": closing_scores,
        "先行力スコア": lead_scores
    })

    result.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"✅ スコア算出完了: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
