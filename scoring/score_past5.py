import argparse
import numpy as np
import pandas as pd
from pathlib import Path

from preprocess.utils import (
    parse_distance,
    time_to_seconds,
    convert_distance_time,
    parse_position,
)
from preprocess.race_filename import (
    parse_race_meta_from_filename,
    STAGE_RAW,
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
    s = series.replace(0, np.nan)
    mean = s.mean()
    std = s.std()
    if std == 0 or pd.isna(std):
        std = 0.01
    dev = 50 + 10 * ((s - mean) / std)
    return dev.fillna(50).round(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument(
        "--input_csv",
        required=True,
        help="crawl で生成された raw.csv のパス",
    )
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"input_csv が存在しません: {input_path}")

    # ------------------------------
    # filename → meta（唯一の正）
    # ------------------------------
    meta = parse_race_meta_from_filename(input_path.name)
    if meta["stage"] != STAGE_RAW:
        raise RuntimeError("raw.csv を入力してください")

    distance = meta["distance"]
    surface = meta["surface"]
    field_size = meta["field_size"]

    print(
        f"🧠 score_past5 条件: "
        f"{surface}{distance}m / {field_size}頭"
    )

    # ------------------------------
    # 入力 CSV 読み込み
    # ------------------------------
    df = pd.read_csv(input_path)

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

            # speed / closing（馬場一致のみ）
            if surface_past == surface:
                dist = parse_distance(dist_raw)
                time_sec = time_to_seconds(time_raw)

                if dist and time_sec:
                    adj = convert_distance_time(
                        time_sec, dist, distance, surface_past
                    )
                    if adj:
                        speeds.append(adj)

                if not pd.isna(agari):
                    base = 60 - float(agari)
                    base += PACE_CORRECTION_CLOSING.get(pace, 0)
                    closings.append(base)

            # lead（馬場無関係）
            pos = parse_position(passage, field_size=field_size)
            if pos is not None:
                new_lead = pos + PACE_CORRECTION_LEAD_NEW.get(pace, 0)
                new_lead = max(0, min(1, new_lead))
                leads.append(new_lead)

        raw_speed = 200 - np.mean(speeds) if speeds else 0
        raw_closing = np.mean(closings) if closings else 0
        raw_lead = np.mean(leads) if leads else 0

        raw_speed_list.append(round(raw_speed, 4))
        raw_closing_list.append(round(raw_closing, 4))
        raw_lead_list.append(round(raw_lead, 4))

    # ------------------------------
    # 出力
    # ------------------------------
    out = pd.DataFrame({
        "馬名": df["馬名"],
        "raw_speed": raw_speed_list,
        "raw_closing": raw_closing_list,
        "raw_lead": raw_lead_list,
    })

    out["speed_dev"] = to_deviation(out["raw_speed"])
    out["closing_dev"] = to_deviation(out["raw_closing"])
    out["lead_dev"] = to_deviation(out["raw_lead"])

    output_path = (
        ASSETS /
        f"race_{meta['race_id']}_{meta['course']}_"
        f"{surface}{distance}m_5runs_scores.csv"
    )

    out.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ score_past5 出力完了: {output_path}")


if __name__ == "__main__":
    main()
