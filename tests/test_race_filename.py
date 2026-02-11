from preprocess.race_filename import (
    build_raw_filename,
    build_5runs_filename,
    build_course_score_filename,
    parse_race_meta_from_filename,
    STAGE_RAW,
    STAGE_5RUNS,
    STAGE_COURSE,
)


def test_build_and_parse_raw():
    filename = build_raw_filename(
        race_id="202506050211",
        course="中山",
        surface="芝",
        distance=1200,
        field_size=16,
    )

    meta = parse_race_meta_from_filename(filename)

    assert meta["race_id"] == "202506050211"
    assert meta["course"] == "中山"
    assert meta["surface"] == "芝"
    assert meta["distance"] == 1200
    assert meta["field_size"] == 16
    assert meta["stage"] == STAGE_RAW


def test_build_and_parse_5runs():
    filename = build_5runs_filename(
        race_id="202506050211",
        course="中山",
        surface="芝",
        distance=1200,
    )

    meta = parse_race_meta_from_filename(filename)

    assert meta["stage"] == STAGE_5RUNS
    assert meta["field_size"] is None


def test_build_and_parse_course_score():
    filename = build_course_score_filename(
        race_id="202506050211",
        course="中山",
        surface="芝",
        distance=1200,
    )

    meta = parse_race_meta_from_filename(filename)

    assert meta["stage"] == STAGE_COURSE


def test_invalid_filename_should_fail():
    invalid = "race_202506050211_芝1200m_raw.csv"

    try:
        parse_race_meta_from_filename(invalid)
        assert False, "ここに来たら失敗"
    except ValueError:
        pass
