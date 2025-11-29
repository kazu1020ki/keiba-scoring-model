# 競馬予想モデル/preprocess/utils.py
"""
前処理系の共通ユーティリティ関数群
 - 距離パース
 - タイム変換
 - 距離換算
 - 通過順位→割合
"""

import pandas as pd

FURLONG = 200        # 1F = 200m
DIST_ADJ = 0.4       # 距離補正：1Fズレるごとに +0.4 秒


def parse_distance(dist_str):
    """
    '芝1400', 'ダ1200', '1400m' などから距離の数字だけ抽出して int を返す
    """
    if pd.isna(dist_str):
        return None

    dist_str = str(dist_str)
    digits = ''.join([c for c in dist_str if c.isdigit()])

    return int(digits) if digits else None


def time_to_seconds(t):
    """
    '1:33.5' → 93.5 のように秒数へ変換
    """
    if pd.isna(t):
        return None

    try:
        m, s = str(t).split(":")
        return int(m) * 60 + float(s)
    except Exception:
        return None


def convert_distance_time(time_sec, race_dist, target_dist, furlong: int = FURLONG, dist_adj: float = DIST_ADJ):
    """
    任意の距離のタイムを target_dist に換算し、距離補正を加える
    time_sec : 元タイム（秒）
    race_dist: 元の距離（m）
    target_dist: 換算先の距離（m）
    """
    if time_sec is None or race_dist is None or target_dist is None:
        return None

    base = time_sec * (target_dist / race_dist)

    # 距離差分の補正
    diff_f = abs(target_dist - race_dist) / furlong
    corrected = base + diff_f * dist_adj

    return corrected


def parse_position(pos_str, field_size: int):
    """
    通過順位文字列 '1-3-2-1' などから先頭コーナーの通過順位を取り、
    フルゲートに対する割合（前に行くほど高い）を算出する。
    """
    if pd.isna(pos_str):
        return None

    try:
        first = int(str(pos_str).split("-")[0])
        return 1 - (first / field_size)
    except Exception:
        return None
