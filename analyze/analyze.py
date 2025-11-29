import pandas as pd
import numpy as np

# ==============================
# ▼ 手動設定
# ==============================
TARGET_DIST = 2400   # ← ここを予想レースの距離に変更する（例: 1200, 1800など）

FURLONG = 200        # 1F = 200m
DIST_ADJ = 0.4       # 距離補正：1Fズレるごとに +0.4 秒
FIELD_SIZE = 18      # 想定フルゲート（通過順位の割合計算用）

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
# ▼ ユーティリティ関数
# ==============================

def parse_distance(dist_str):
    """
    '芝1400', 'ダ1200', '1400m' などから距離の数字だけ抽出
    """
    if pd.isna(dist_str):
        return None

    dist_str = str(dist_str)
    digits = ''.join([c for c in dist_str if c.isdigit()])

    return int(digits) if digits else None


def time_to_seconds(t):
    """
    '1:33.5' → 93.5
    """
    if pd.isna(t):
        return None

    try:
        m, s = str(t).split(":")
        return int(m) * 60 + float(s)
    except:
        return None


def convert_distance_time(time_sec, race_dist):
    """
    出走距離にタイムを換算し、距離補正を加える
    """
    if time_sec is None or race_dist is None:
        return None

    base = time_sec * (TARGET_DIST / race_dist)

    # 距離差分の補正
    diff_f = abs(TARGET_DIST - race_dist) / FURLONG
    corrected = base + diff_f * DIST_ADJ

    return corrected


def parse_position(pos_str, field_size=FIELD_SIZE):
    """
    '1-3-2-1' → 先頭の通過順位 → 割合化
    """
    if pd.isna(pos_str):
        return None

    try:
        first = int(str(pos_str).split("-")[0])
        return 1 - (first / field_size)
    except:
        return None


# ==============================
# ▼ メイン処理
# ==============================

df = pd.read_csv("shutuba_with_past5.csv")

speed_scores = []
closing_scores = []
lead_scores = []

for i, row in df.iterrows():

    speeds = []
    closings = []
    leads = []

    for n in range(1, 6):

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
        adjusted_time = convert_distance_time(time_sec, dist)
        if adjusted_time is not None:
            speeds.append(adjusted_time)

        # ========= 上がり力評価 =========
        if not pd.isna(agari):
            agari = float(agari)
            base = 60 - agari   # 上がりが速いほど高評価
            base += PACE_CORRECTION_CLOSING.get(pace, 0)
            closings.append(base)

        # ========= 先行力評価 =========
        pos_val = parse_position(passage)
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

result.to_csv("shutuba_with_scores.csv", index=False, encoding="utf-8-sig")

print("✅ スコア算出完了：shutuba_with_scores.csv を出力しました！")
