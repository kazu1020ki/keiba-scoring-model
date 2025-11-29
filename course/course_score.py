import argparse
import json
import pandas as pd
from pathlib import Path

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--course", required=True)   # 東京・中山・京都 など
    parser.add_argument("--surface", required=True)  # 芝 or ダ
    args = parser.parse_args()

    INPUT = ASSETS / f"race_{args.race_id}_{args.distance}m_scores.csv"
    OUTPUT = ASSETS / f"race_{args.race_id}_{args.distance}m_{args.course}_course.csv"

    df = pd.read_csv(INPUT)

    # ------------------------------
    #   コース重みを config から取得
    # ------------------------------
    weight = load_course_weight(args.course, args.surface, args.distance)
    w_speed = weight["speed"]
    w_lead = weight["lead"]
    w_close = weight["closing"]

    # ------------------------------
    #   最終スコア算出
    # ------------------------------
    scores = []
    for _, row in df.iterrows():
        sp = row["スピードスコア"]
        cl = row["上がり力スコア"]
        ld = row["先行力スコア"]

        if any(pd.isna([sp, cl, ld])):
            scores.append(None)
            continue

        final = sp * w_speed + ld * w_lead + cl * w_close
        scores.append(round(final, 3))

    df[f"{args.course}適性スコア"] = scores
    df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

    print(f"✅ コース適性スコアを出力: {OUTPUT}")


if __name__ == "__main__":
    main()
