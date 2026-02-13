from pathlib import Path

import pandas as pd

from web.app import _build_result


def test_build_result_ranking(tmp_path: Path):
    csv_path = tmp_path / "race_202401010101_東京_芝1600m_course_scores.csv"
    df = pd.DataFrame(
        {
            "馬名": ["A", "B", "C"],
            "東京適性スコア": [61.2, 58.0, 61.2],
        }
    )
    df.to_csv(csv_path, index=False)

    result = _build_result(csv_path)

    assert result["race"]["race_id"] == "202401010101"
    assert result["race"]["course"] == "東京"
    assert result["ranking"][0]["rank"] == 1
    assert result["ranking"][1]["rank"] == 1
    assert result["ranking"][2]["rank"] == 2
