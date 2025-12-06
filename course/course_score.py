# course/course_score.py
# 偏差値化 + raw併存 + 列名互換性維持版

import argparse
import json
import pandas as pd
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT_ROOT / "assets"
CONFIG_DIR = PROJECT_ROOT / "config"


def load_course_weight(course: str, surface: str, distance: int):
    """コース重みを config/course_weight.json から読み込む"""
    config_path = CONFIG_DIR / "course_weight.json"
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    key = f"{surface}{distance}"  # 例: "芝1600"

    if course not in config:
        raise ValueError(f"コース '{course}' の重みが config にありません")

    if key not in config[course]:
        raise ValueError(f"{course} の '{key}' 用の重み設定がありません")

    return config[course][key]  # speed / lead / closing


def to_deviation(series: pd.Series) -> pd.Series:
    """一次スコアを偏差値化（std=0対策・NaN=50補正、round(2)）"""
    s = series.replace(0, np.nan)

    mean = s.mean()
    std = s.std()

    if std == 0 or pd.isna(std):
        std = 0.01

    dev = 50 + 10 * ((s - mean) / std)
    dev = dev.fillna(50)

    return dev.round(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--course", required=True)   # 東京・中山・京都など
    parser.add_argument("--surface", required=True)  # 芝 or ダ
    args = parser.parse_args()

    INPUT = ASSETS / f"race_{args.race_id}_{args.distance}m_scores.csv"
    OUTPUT = ASSETS / f"race_{args.race_id}_{args.distance}m_{args.course}_course.csv"

    df = pd.read_csv(INPUT)

    # ------------------------------
    #   コース重み読み込み
    # ------------------------------
    weight = load_course_weight(args.course, args.surface, args.distance)
    w_speed = weight["speed"]
    w_lead = weight["lead"]
    w_close = weight["closing"]

    # ------------------------------
    #   一次スコア（raw）計算
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

    df["raw_course_score"] = raw_scores  # デバッグ用

    # ------------------------------
    #   最終偏差値（コース適性スコア）
    # ------------------------------
    df[f"{args.course}適性スコア"] = to_deviation(df["raw_course_score"])

    # ------------------------------
    #   保存
    # ------------------------------
    df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"✅ コース適性スコア出力完了: {OUTPUT}")


if __name__ == "__main__":
    main()
