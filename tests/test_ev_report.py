import pytest

pytest.importorskip("pandas")

from pathlib import Path

import pandas as pd

from predict.ev_report import EVConfig, generate_ev_reports


def _write_fixture_files(asset_dir: Path):
    raw = pd.DataFrame(
        {
            "馬番": [1, 2, 3, 4, 5, 6],
            "馬名": ["A", "B", "C", "D", "E", "F"],
            "オッズ": [3.2, 8.1, 15.0, 45.0, 120.0, ""],
        }
    )
    raw.to_csv(
        asset_dir / "race_202401010101_東京_芝1600m_6_raw.csv",
        index=False,
        encoding="utf-8-sig",
    )

    score = pd.DataFrame(
        {
            "馬名": ["A", "B", "C", "D", "E", "F"],
            "東京適性スコア": [62, 59, 56, 53, 50, 47],
        }
    )
    score.to_csv(
        asset_dir / "race_202401010101_東京_芝1600m_course_scores.csv",
        index=False,
        encoding="utf-8-sig",
    )


def test_generate_ev_reports_outputs_expected_files(tmp_path: Path, monkeypatch):
    asset_dir = tmp_path / "assets"
    out_dir = tmp_path / "outputs"
    asset_dir.mkdir()
    out_dir.mkdir()
    _write_fixture_files(asset_dir)

    monkeypatch.setattr("predict.ev_report.ASSETS", asset_dir)
    monkeypatch.setattr("predict.ev_report.OUTPUTS", out_dir)

    win_out, wide_out = generate_ev_reports(
        race_id="202401010101",
        config=EVConfig(n_sim=3000, random_seed=7),
    )

    assert win_out.exists()
    assert wide_out.exists()

    win_df = pd.read_csv(win_out)
    assert set(["ev_win", "m_required", "decision", "ev_risk_adj", "p_mkt", "cap_ratio_used"]).issubset(win_df.columns)
    assert len(win_df) == 6
    assert win_df.loc[win_df["horse_name"] == "F", "decision"].iloc[0] == "NO_BUY"

    # 低オッズ高スコア馬はEVが正になりやすい設定
    ev_a = win_df.loc[win_df["horse_name"] == "A", "ev_win"].iloc[0]
    assert ev_a > 0

    # 大穴側はキャップが効き、調整後確率が上限以下になる
    row_e = win_df.loc[win_df["horse_name"] == "E"].iloc[0]
    assert row_e["p_adj"] <= row_e["p_mkt"] * row_e["cap_ratio_used"] + 1e-12

    wide_df = pd.read_csv(wide_out)
    assert len(wide_df) == 10
    assert wide_df["priority"].sum() == 6
    assert wide_df["p_wide"].notna().all()
    assert wide_df["o_min"].notna().all()
