# scoring/score_past5.py
# 偏差値化 + raw併存 + 中立補正 + leadクリップ + 有効数字統一版

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


def to_deviation(series: pd.Series) -> pd.Series:
    """
    レース内偏差値化（0はNaN扱い → 最後に50補正）
    小数第2位に丸める
    """
    # 0 はデータ無しとして扱う
    s = series.replace(0, np.nan)

    mean = s.mean()
    std = s.std()

    if std == 0 or pd.isna(std):
        std = 0.01

    dev = 50 + 10 * ((s - mean) / std)

    # データ無し(=NaN)は偏差値50に補正
    dev = dev.fillna(50)

    # 小数第2位に統一
    return dev.round(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--field_size", type=int, default=16)
    parser.add_argument("--surface", required=True)  # 予想馬場(芝/ダ)
    args = parser.parse_args()

    INPUT = ASSETS / f"race_{args.race_id}_raw.csv"
    OUTPUT = ASSETS / f"race_{args.race_id}_{args.distance}m_scores.csv"

    df = pd.read_csv(INPUT)

    raw_speed_list = []
    raw_closing_list = []
    raw_lead_list = []

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

                if dist and time_sec:
                    adj = convert_distance_time(time_sec, dist, args.distance, surface_past)
                    if adj:
                        speeds.append(adj)

                if not pd.isna(agari):
                    base = 60 - float(agari)
                    base += PACE_CORRECTION_CLOSING.get(pace, 0)
                    closings.append(base)

            # ---------------------------
            # lead → 馬場無関係で使う
            # ---------------------------
            pos = parse_position(passage, field_size=args.field_size)
            if pos is not None:
                new_lead = pos + PACE_CORRECTION_LEAD_NEW.get(pace, 0)

                # ★ リード値は 0〜1 にクリップ
                new_lead = max(0, min(1, new_lead))
                leads.append(new_lead)

        # -------------------------------
        # raw スコア（空なら 0）
        # -------------------------------
        raw_speed = 200 - np.mean(speeds) if speeds else 0
        raw_closing = np.mean(closings) if closings else 0
        raw_lead = np.mean(leads) if leads else 0

        raw_speed_list.append(round(raw_speed, 4))
        raw_closing_list.append(round(raw_closing, 4))
        raw_lead_list.append(round(raw_lead, 4))

    # -------------------------------
    # DataFrame 化
    # -------------------------------
    out = pd.DataFrame({
        "馬名": df["馬名"],
        "raw_speed": raw_speed_list,
        "raw_closing": raw_closing_list,
        "raw_lead": raw_lead_list,
    })

    # -------------------------------
    # 偏差値列（dev）
    # -------------------------------
    out["speed_dev"] = to_deviation(out["raw_speed"])
    out["closing_dev"] = to_deviation(out["raw_closing"])
    out["lead_dev"] = to_deviation(out["raw_lead"])

    # -------------------------------
    # 出力
    # -------------------------------
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"✅ 偏差値スコア出力完了: {OUTPUT}")


if __name__ == "__main__":
    main()
