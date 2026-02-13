from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from webapp import server


def test_find_latest_report_returns_newest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()

    older = report_dir / "report_01R_東京_芝1600m_202401010101.txt"
    newer = report_dir / "report_02R_東京_芝1600m_202401010101.txt"
    older.write_text("old", encoding="utf-8")
    newer.write_text("new", encoding="utf-8")

    monkeypatch.setattr(server, "REPORT_DIR", report_dir)

    assert server.find_latest_report("202401010101") == newer
