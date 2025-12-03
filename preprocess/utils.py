# preprocess/utils.py
"""
前処理系ユーティリティ
 - 距離パース
 - タイム変換
 - 距離換算（A案：芝0.4 / ダ0.7）
 - 通過順位 → 割合
"""

import pandas as pd

FURLONG = 200        # 1F = 200m


def parse_distance(dist_str):
    """'芝1400', 'ダ1200', '1400m' などから距離の数字だけ抽出"""
    if pd.isna(dist_str):
        return None

    dist_str = str(dist_str)
    digits = ''.join([c for c in dist_str if c.isdigit()])
    return int(digits) if digits else None


def time_to_seconds(t):
    """'1:33.5' を 93.5秒に変換"""
    if pd.isna(t):
        return None

    try:
        m, s = str(t).split(":")
        return int(m) * 60 + float(s)
    except Exception:
        return None


def convert_distance_time(time_sec, race_dist, target_dist, surface):
    """
    任意の距離のタイムを target_dist に換算。
    A案：距離差1Fごとに
        ・芝：+0.4秒
        ・ダ：+0.7秒 に補正。
    """
    if time_sec is None or race_dist is None or target_dist is None:
        return None

    # 距離比による線形換算
    base = time_sec * (target_dist / race_dist)

    # 距離差 → 何F違うか
    diff_f = abs(target_dist - race_dist) / FURLONG

    # 馬場別補正係数（A案）
    if surface == "芝":
        dist_adj = 0.4
    else:
        dist_adj = 0.7  # ダートは強めの補正

    corrected = base + diff_f * dist_adj
    return corrected


def parse_position(pos_str, field_size: int):
    """
    '1-3-2-1' → 最初の通過順位を取り、前に行くほど高い割合へ変換
    """
    if pd.isna(pos_str):
        return None

    try:
        first = int(str(pos_str).split("-")[0])
        return 1 - (first / field_size)
    except Exception:
        return None
