# scoring/score_past5.py（A案距離補正 + 馬場フィルタ + 0埋め 完全統合版）

import argparse
import numpy as np
import pandas as pd
from pathlib import Path

from preprocess.utils import (
    parse_distance, time_to_seconds, convert_distance_time, parse_position
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT_ROOT / "assets"

PACE_CORRECTION_CLOSING = {"ハイ": -8, "ミドル": 0, "スロー": 8}
PACE_CORRECTION_LEAD_NEW = {"ハイ": 0.1, "ミドル": 0, "スロー": -0.1}


def detect_surface(dist_raw: str):
    """'芝1600' 'ダ1200' などから馬場を判定"""
    if pd.isna(dist_raw):
        return None
    s = str(dist_raw)
    if "芝" in s:
        return "芝"
    if "ダ" in s or "砂" in s:
        return "ダ"
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--field_size", type=int, default=16)
    parser.add_argument("--surface", required=True)  # 予想馬場
    args = parser.parse_args()

    INPUT = ASSETS / f"race_{args.race_id}_raw.csv"
    OUTPUT = ASSETS / f"race_{args.race_id}_{args.distance}m_scores.csv"

    df = pd.read_csv(INPUT)

    speed_scores = []
    closing_scores = []
    lead_scores = []

    for _, row in df.iterrows():
        speeds = []
        closings = []
        leads = []

        for n in range(1, 6):
            dist_raw = row.get(f"{n}走前_距離")
            time_raw = row.get(f"{n}走前_タイム")
            agari = row.get(f"{n}走前_上り")
            pace = row.get(f"{n}走前_ペース")
            passage = row.get(f"{n}走前_通過")

            surface_past = detect_surface(dist_raw)

            # ---------------------------
            # speed / closing → 馬場一致のみ
            # ---------------------------
            if surface_past == args.surface:
                dist = parse_distance(dist_raw)
                time_sec = time_to_seconds(time_raw)

                # A案距離補正（surface_past を渡す）
                if dist and time_sec:
                    adj = convert_distance_time(
                        time_sec,
                        dist,
                        args.distance,
                        surface_past
                    )
                    if adj:
                        speeds.append(adj)

                if not pd.isna(agari):
                    base = 60 - float(agari)
                    base += PACE_CORRECTION_CLOSING.get(pace, 0)
                    closings.append(base)

            # ---------------------------
            # lead → 馬場関係なく常に使用
            # ---------------------------
            pos = parse_position(passage, field_size=args.field_size)
            if pos is not None:
                new_lead = pos + PACE_CORRECTION_LEAD_NEW.get(pace, 0)
                leads.append(new_lead)

        # -------------------------------
        # 対象0 → スコア0（None禁止）
        # -------------------------------
        speed_scores.append(round(200 - np.mean(speeds), 2) if speeds else 0)
        closing_scores.append(round(np.mean(closings), 2) if closings else 0)
        lead_scores.append(round(np.mean(leads), 4) if leads else 0.0)

    out = pd.DataFrame({
        "馬名": df["馬名"],
        "スピードスコア": speed_scores,
        "上がり力スコア": closing_scores,
        "先行力スコア": lead_scores,
    })

    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"✅ 出力: {OUTPUT}")


if __name__ == "__main__":
    main()
