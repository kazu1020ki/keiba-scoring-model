import argparse
import itertools
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from preprocess.race_filename import parse_race_meta_from_filename

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT_ROOT / "assets"
OUTPUTS = PROJECT_ROOT / "outputs"
OUTPUTS.mkdir(exist_ok=True)


@dataclass(frozen=True)
class EVConfig:
    temperature: float = 10.0
    lambda_risk: float = 0.05
    n_sim: int = 20000
    m_wide: float = 0.06
    wide_top_k: int = 5
    wide_priority_top_n: int = 6
    random_seed: int = 42

    beta_bands: tuple[tuple[float, float], ...] = (
        (10.0, 0.92),
        (30.0, 0.70),
        (100.0, 0.50),
        (300.0, 0.30),
        (float("inf"), 0.20),
    )

    cap_ratio_bands: tuple[tuple[float, float], ...] = (
        (10.0, 1.60),
        (30.0, 1.20),
        (100.0, 1.00),
        (300.0, 0.75),
        (float("inf"), 0.55),
    )

    m_required_bands: tuple[tuple[float, float], ...] = (
        (10.0, 0.02),
        (30.0, 0.08),
        (100.0, 0.18),
        (float("inf"), 0.30),
    )


def _band_value(value: float, bands: tuple[tuple[float, float], ...]) -> float:
    for upper, out in bands:
        if value < upper:
            return out
    return bands[-1][1]


def _safe_softmax(scores: pd.Series, temperature: float) -> pd.Series:
    scaled = scores.astype(float) / temperature
    scaled = scaled - scaled.max()
    exps = np.exp(scaled)
    return exps / exps.sum()


def _coerce_numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(",", "", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def _load_inputs(race_id: str) -> tuple[dict, pd.DataFrame, pd.DataFrame, str]:
    raw_candidates = list(ASSETS.glob(f"race_{race_id}_*_raw.csv"))
    if not raw_candidates:
        raise FileNotFoundError(f"raw.csv が見つかりません: race_id={race_id}")
    if len(raw_candidates) > 1:
        raise RuntimeError(f"raw.csv が複数見つかりました: {raw_candidates}")

    raw_path = raw_candidates[0]
    meta = parse_race_meta_from_filename(raw_path.name)

    course_score_path = ASSETS / (
        f"race_{race_id}_{meta['course']}_{meta['surface']}{meta['distance']}m_course_scores.csv"
    )
    if not course_score_path.exists():
        raise FileNotFoundError(f"course_scores.csv が見つかりません: {course_score_path}")

    raw_df = pd.read_csv(raw_path)
    score_df = pd.read_csv(course_score_path)
    score_col = f"{meta['course']}適性スコア"

    if score_col not in score_df.columns:
        raise KeyError(f"スコア列が存在しません: {score_col}")

    return meta, raw_df, score_df, score_col


def _simulate_top3_indices(probs: np.ndarray, n_sim: int, rng: np.random.Generator) -> np.ndarray:
    n_horses = len(probs)
    top3 = np.empty((n_sim, 3), dtype=int)

    for s in range(n_sim):
        remaining = np.arange(n_horses)
        current_probs = probs.copy()

        for k in range(3):
            pick_pos = rng.choice(len(remaining), p=current_probs / current_probs.sum())
            top3[s, k] = remaining[pick_pos]
            remaining = np.delete(remaining, pick_pos)
            current_probs = np.delete(current_probs, pick_pos)

    return top3


def generate_ev_reports(race_id: str, config: EVConfig = EVConfig()) -> tuple[Path, Path]:
    meta, raw_df, score_df, score_col = _load_inputs(race_id)

    merged = score_df[["馬名", score_col]].merge(
        raw_df[["馬番", "馬名", "オッズ"]],
        on="馬名",
        how="left",
    )
    merged = merged.rename(columns={"馬番": "umaban", "馬名": "horse_name", score_col: "score", "オッズ": "win_odds"})

    merged["score"] = pd.to_numeric(merged["score"], errors="coerce")
    merged["win_odds"] = _coerce_numeric(merged["win_odds"])
    merged["umaban"] = pd.to_numeric(merged["umaban"], errors="coerce")

    valid_score_mask = merged["score"].notna()
    merged["p_raw"] = np.nan
    if valid_score_mask.any():
        merged.loc[valid_score_mask, "p_raw"] = _safe_softmax(
            merged.loc[valid_score_mask, "score"], config.temperature
        ).values

    n_horses = int(valid_score_mask.sum())
    uniform = 1.0 / n_horses if n_horses > 0 else np.nan

    merged["beta_used"] = merged["win_odds"].apply(
        lambda x: _band_value(x, config.beta_bands) if pd.notna(x) else np.nan
    )
    merged["p_mkt"] = np.where(
        merged["win_odds"].notna() & (merged["win_odds"] > 0),
        1.0 / merged["win_odds"],
        np.nan,
    )
    merged["cap_ratio_used"] = merged["win_odds"].apply(
        lambda x: _band_value(x, config.cap_ratio_bands) if pd.notna(x) else np.nan
    )

    p_mix = np.where(
        merged["win_odds"].notna() & merged["p_raw"].notna() & pd.notna(uniform),
        merged["beta_used"] * merged["p_raw"] + (1 - merged["beta_used"]) * uniform,
        np.nan,
    )
    p_cap = merged["p_mkt"] * merged["cap_ratio_used"]
    merged["p_adj"] = np.where(
        pd.notna(p_mix) & pd.notna(p_cap),
        np.minimum(p_mix, p_cap),
        p_mix,
    )

    merged["ev_win"] = np.where(
        merged["p_adj"].notna() & merged["win_odds"].notna(),
        merged["p_adj"] * merged["win_odds"] - 1,
        np.nan,
    )
    merged["m_required"] = merged["win_odds"].apply(
        lambda x: _band_value(x, config.m_required_bands) if pd.notna(x) else np.nan
    )
    merged["decision"] = np.where(
        merged["ev_win"].notna() & merged["m_required"].notna() & (merged["ev_win"] >= merged["m_required"]),
        "BUY",
        "NO_BUY",
    )
    merged["ev_risk_adj"] = np.where(
        merged["ev_win"].notna() & merged["win_odds"].notna() & (merged["win_odds"] > 0),
        merged["ev_win"] - config.lambda_risk * np.log(merged["win_odds"]),
        np.nan,
    )

    merged["rank_ev"] = merged["ev_win"].rank(method="min", ascending=False)
    merged["rank_risk"] = merged["ev_risk_adj"].rank(method="min", ascending=False)
    merged["score_rank"] = merged["score"].rank(method="min", ascending=False)
    merged["pop_rank"] = merged["win_odds"].rank(method="min", ascending=True)

    if merged["win_odds"].isna().any():
        logging.warning("win_odds 欠損/不正値あり: ev を NaN として NO_BUY で出力します")

    win_out = OUTPUTS / f"race_{race_id}_win_all.csv"
    merged.sort_values(["rank_ev", "score_rank", "umaban"], na_position="last").to_csv(
        win_out,
        index=False,
        encoding="utf-8-sig",
    )

    wide_out = _build_wide_sheet(race_id, merged, config)
    return win_out, wide_out


def _build_wide_sheet(race_id: str, merged: pd.DataFrame, config: EVConfig) -> Path:
    top = merged.dropna(subset=["score"]).sort_values(["score", "umaban"], ascending=[False, True]).head(config.wide_top_k)
    wide_out = OUTPUTS / f"race_{race_id}_wide_input.csv"

    if len(top) < 5:
        logging.warning("頭数不足のため wide 確率計算不可: p_wide/o_min を NaN で出力")
        pairs = _build_pairs_dataframe(top)
        pairs["p_wide"] = np.nan
        pairs["o_min"] = np.nan
    else:
        p_raw = _safe_softmax(top["score"], config.temperature).to_numpy()
        try:
            rng = np.random.default_rng(config.random_seed)
            top3 = _simulate_top3_indices(p_raw, config.n_sim, rng)
            pairs = _build_pairs_dataframe(top)
            p_values = []
            for _, row in pairs.iterrows():
                idx_a = int(row["idx_a"])
                idx_b = int(row["idx_b"])
                contains_a = (top3 == idx_a).any(axis=1)
                contains_b = (top3 == idx_b).any(axis=1)
                p_values.append(float(np.mean(contains_a & contains_b)))

            pairs["p_wide"] = p_values
            pairs["o_min"] = np.where(
                pairs["p_wide"] > 0,
                (1 + config.m_wide) / pairs["p_wide"],
                np.nan,
            )
        except Exception as exc:
            logging.warning("wide シミュレーション失敗: %s", exc)
            pairs = _build_pairs_dataframe(top)
            pairs["p_wide"] = np.nan
            pairs["o_min"] = np.nan

    pairs = pairs.sort_values("p_wide", ascending=False, na_position="last").reset_index(drop=True)
    pairs["priority"] = (pairs.index < config.wide_priority_top_n).astype(int)
    pairs["wide_odds"] = np.nan
    pairs["ev_wide"] = np.nan
    pairs["decision"] = ""

    out_cols = [
        "priority", "pair_id",
        "umaban_a", "horse_a", "score_a",
        "umaban_b", "horse_b", "score_b",
        "p_wide", "o_min",
        "wide_odds", "ev_wide", "decision",
    ]
    pairs[out_cols].to_csv(wide_out, index=False, encoding="utf-8-sig")
    return wide_out


def _build_pairs_dataframe(top: pd.DataFrame) -> pd.DataFrame:
    working = top.reset_index(drop=True).copy()
    working["label"] = [chr(ord("A") + i) for i in range(len(working))]

    rows = []
    for i, j in itertools.combinations(range(len(working)), 2):
        a = working.iloc[i]
        b = working.iloc[j]
        rows.append({
            "pair_id": f"{a['label']}-{b['label']}",
            "idx_a": i,
            "idx_b": j,
            "umaban_a": int(a["umaban"]) if pd.notna(a["umaban"]) else np.nan,
            "horse_a": a["horse_name"],
            "score_a": a["score"],
            "umaban_b": int(b["umaban"]) if pd.notna(b["umaban"]) else np.nan,
            "horse_b": b["horse_name"],
            "score_b": b["score"],
        })

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--temperature", type=float, default=EVConfig.temperature)
    parser.add_argument("--lambda_risk", type=float, default=EVConfig.lambda_risk)
    parser.add_argument("--n_sim", type=int, default=EVConfig.n_sim)
    parser.add_argument("--m_wide", type=float, default=EVConfig.m_wide)
    parser.add_argument("--random_seed", type=int, default=EVConfig.random_seed)
    args = parser.parse_args()

    config = EVConfig(
        temperature=args.temperature,
        lambda_risk=args.lambda_risk,
        n_sim=args.n_sim,
        m_wide=args.m_wide,
        random_seed=args.random_seed,
    )

    win_out, wide_out = generate_ev_reports(args.race_id, config)
    print(f"✅ 単勝EV出力: {win_out}")
    print(f"✅ ワイド入力シート出力: {wide_out}")


if __name__ == "__main__":
    main()
