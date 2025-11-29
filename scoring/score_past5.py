# scoring/score_past5.py（新 lead 正式版）

import argparse
import numpy as np
import pandas as pd
from pathlib import Path

from preprocess.utils import (
    parse_distance, time_to_seconds, convert_distance_time, parse_position
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT_ROOT / "assets"

# 旧：±8 / ±10 → スケール大きすぎ
PACE_CORRECTION_CLOSING = {"ハイ": -8, "ミドル": 0, "スロー": 8}

# ★新 lead ペース補正（±0.1）
PACE_CORRECTION_LEAD_NEW = {"ハイ": 0.1, "ミドル": 0, "スロー": -0.1}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--field_size", type=int, default=16)
    args = parser.parse_args()

    INPUT = ASSETS / f"race_{args.race_id}_raw.csv"
    OUTPUT = ASSETS / f"race_{args.race_id}_{args.distance}m_scores.csv"

    df = pd.read_csv(INPUT)

    speed_scores = []
    closing_scores = []
    lead_scores = []   # ← 新 lead（0〜1＋補正）

    for _, row in df.iterrows():
        speeds, closings, leads = [], [], []

        for n in range(1, 6):
            dist_raw = row.get(f"{n}走前_距離")
            time_raw = row.get(f"{n}走前_タイム")
            agari = row.get(f"{n}走前_上り")
            pace = row.get(f"{n}走前_ペース")
            passage = row.get(f"{n}走前_通過")

            # ----------------------
            # speed（現状維持）
            # ----------------------
            dist = parse_distance(dist_raw)
            time_sec = time_to_seconds(time_raw)

            if dist and time_sec:
                adj = convert_distance_time(time_sec, dist, args.distance)
                speeds.append(adj)

            # ----------------------
            # closing（現状維持）
            # ----------------------
            if not pd.isna(agari):
                base = 60 - float(agari)
                base += PACE_CORRECTION_CLOSING.get(pace, 0)
                closings.append(base)

            # ----------------------
            # ★新 lead：0〜1 ＋ ±0.1補正
            # ----------------------
            pos = parse_position(passage, field_size=args.field_size)
            if pos is not None:
                new_lead = pos + PACE_CORRECTION_LEAD_NEW.get(pace, 0)
                leads.append(new_lead)

        # ===========================
        # 最終スコア（平均）
        # ===========================
        speed_scores.append(round(200 - np.mean(speeds), 2) if speeds else None)
        closing_scores.append(round(np.mean(closings), 2) if closings else None)
        lead_scores.append(round(np.mean(leads), 4) if leads else None)  # 小数4桁推奨

    out = pd.DataFrame({
        "馬名": df["馬名"],
        "スピードスコア": speed_scores,
        "上がり力スコア": closing_scores,
        "先行力スコア": lead_scores  # ← 新 lead 値
    })

    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"✅ 出力: {OUTPUT}")


if __name__ == "__main__":
    main()
