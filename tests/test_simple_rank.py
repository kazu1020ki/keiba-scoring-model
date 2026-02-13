from pathlib import Path

import pytest

from predict.simple_rank import resolve_input_path


def test_resolve_input_path_with_surface(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    target = asset_dir / "race_202401010101_東京_芝1600m_course_scores.csv"
    target.write_text("", encoding="utf-8")

    monkeypatch.setattr("predict.simple_rank.ASSETS", asset_dir)

    resolved = resolve_input_path("202401010101", "東京", 1600, "芝")
    assert resolved == target


def test_resolve_input_path_without_surface_raises_on_multiple(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    (asset_dir / "race_202401010101_東京_芝1600m_course_scores.csv").write_text(
        "", encoding="utf-8"
    )
    (asset_dir / "race_202401010101_東京_ダ1600m_course_scores.csv").write_text(
        "", encoding="utf-8"
    )

    monkeypatch.setattr("predict.simple_rank.ASSETS", asset_dir)

    with pytest.raises(RuntimeError):
        resolve_input_path("202401010101", "東京", 1600, None)
