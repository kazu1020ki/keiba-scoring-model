import argparse
import json
import pandas as pd
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT_ROOT / "assets"
CONFIG_DIR = PROJECT_ROOT / "config"


# ==============================
# utils
# ==============================
def load_course_weight(course: str, surface: str, distance: int):
    """
    コース重みを config/course_weight.json から読み込む
    """
    config_path = CONFIG_DIR / "course_weight.json"
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    key = f"{surface}{distance}"  # 例: "芝1600"

    if course not in config:
        raise ValueError(f"コース '{course}' の重みが config にありません")

    if key not in config[course]:
        raise ValueError(f"{course} の '{key}' 用の重み設定がありません")

    return config[course][key]


def to_deviation(series: pd.Series) -> pd.Series:
    """
    一次スコアを偏差値化（std=0対策・NaN=50補正）
    """
    s = series.replace(0, np.nan)

    mean = s.mean()
    std = s.std()

    if std == 0 or pd.isna(std):
        std = 0.01

    dev = 50 + 10 * ((s - mean) / std)
    return dev.fillna(50).round(2)


def rebalance_weights(w_speed: float, w_lead: float, w_close: float):
    """
    コース重みを比率化し、lead が過剰優位になるケースを緩和する。
    """
    total = w_speed + w_lead + w_close
    if total <= 0:
        raise ValueError("weight の合計が 0 以下です")

    w_speed /= total
    w_lead /= total
    w_close /= total

    lead_cap = 0.42
    if w_lead > lead_cap:
        excess = w_lead - lead_cap
        w_lead = lead_cap

        redistribute = w_speed + w_close
        if redistribute <= 0:
            w_speed += excess / 2
            w_close += excess / 2
        else:
            w_speed += excess * (w_speed / redistribute)
            w_close += excess * (w_close / redistribute)

    return w_speed, w_lead, w_close


# ==============================
# main
# ==============================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--course", required=True)
    parser.add_argument("--surface", required=True)
    parser.add_argument("--distance", type=int, required=True)

    # ★ 当日バイアス（任意）
    parser.add_argument("--bias_speed", type=int, default=0)
    parser.add_argument("--bias_lead", type=int, default=0)
    parser.add_argument("--bias_closing", type=int, default=0)

    args = parser.parse_args()

    # ------------------------------
    # 入出力ファイル（新命名規則）
    # ------------------------------
    INPUT = ASSETS / (
        f"race_{args.race_id}_{args.course}_"
        f"{args.surface}{args.distance}m_5runs_scores.csv"
    )

    OUTPUT = ASSETS / (
        f"race_{args.race_id}_{args.course}_"
        f"{args.surface}{args.distance}m_course_scores.csv"
    )

    if not INPUT.exists():
        raise FileNotFoundError(f"入力CSVが存在しません: {INPUT}")

    df = pd.read_csv(INPUT)

    # ------------------------------
    # コース重み読み込み
    # ------------------------------
    weight = load_course_weight(args.course, args.surface, args.distance)
    w_speed = weight["speed"]
    w_lead = weight["lead"]
    w_close = weight["closing"]

    # ------------------------------
    # 当日バイアス → 係数変換
    # ------------------------------
    bias_map = {
        -2: 0.90,
        -1: 0.95,
         0: 1.00,
         1: 1.05,
         2: 1.10,
    }

    for val in [args.bias_speed, args.bias_lead, args.bias_closing]:
        if val not in bias_map:
            raise ValueError("bias は -2, -1, 0, 1, 2 のいずれか")

    w_speed *= bias_map[args.bias_speed]
    w_lead *= bias_map[args.bias_lead]
    w_close *= bias_map[args.bias_closing]

    w_speed, w_lead, w_close = rebalance_weights(
        w_speed=w_speed,
        w_lead=w_lead,
        w_close=w_close,
    )

    print("=== 使用重み（補正後） ===")
    print(f"speed:   {w_speed}")
    print(f"lead:    {w_lead}")
    print(f"closing: {w_close}")

    # ------------------------------
    # raw コーススコア計算
    # ------------------------------
    raw_scores = []

    for _, row in df.iterrows():
        sp = row["speed_dev"]
        cl = row["closing_dev"]
        ld = row["lead_dev"]

        if any(pd.isna([sp, cl, ld])):
            raw_scores.append(np.nan)
            continue

        raw = sp * w_speed + ld * w_lead + cl * w_close
        raw_scores.append(round(raw, 4))

    df["raw_course_score"] = raw_scores

    # ------------------------------
    # 偏差値化
    # ------------------------------
    df[f"{args.course}適性スコア"] = to_deviation(df["raw_course_score"])

    # ------------------------------
    # 出力
    # ------------------------------
    df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"✅ コース適性スコア出力完了: {OUTPUT}")


if __name__ == "__main__":
    main()
