import re
from pathlib import Path

# ==============================
# Stage constants
# ==============================
STAGE_RAW = "raw"
STAGE_5RUNS = "5runs_scores"
STAGE_COURSE = "course_scores"


# ==============================
# Filename builders
# ==============================
def build_raw_filename(race_id, course, surface, distance, field_size) -> str:
    """
    race_{race_id}_{course}_{surface}{distance}m_{field_size}h_raw.csv
    """
    return (
        f"race_{race_id}_"
        f"{course}_"
        f"{surface}{distance}m_"
        f"{field_size}h_{STAGE_RAW}.csv"
    )


def build_5runs_filename(race_id, course, surface, distance) -> str:
    """
    race_{race_id}_{course}_{surface}{distance}m_5runs_scores.csv
    """
    return (
        f"race_{race_id}_"
        f"{course}_"
        f"{surface}{distance}m_{STAGE_5RUNS}.csv"
    )


def build_course_score_filename(race_id, course, surface, distance) -> str:
    """
    race_{race_id}_{course}_{surface}{distance}m_course_scores.csv
    """
    return (
        f"race_{race_id}_"
        f"{course}_"
        f"{surface}{distance}m_{STAGE_COURSE}.csv"
    )


# ==============================
# Filename → meta parser
# ==============================
RACE_FILENAME_PATTERN = re.compile(
    r"""
    ^race_
    (?P<race_id>\d+)_                # race_id
    (?P<course>[^_]+)_               # course (日本語)
    (?P<surface>[芝ダ])              # surface
    (?P<distance>\d+)m               # distance
    (?:_(?P<field_size>\d+)h)?       # optional field size (raw only)
    _(?P<stage>raw|5runs_scores|course_scores)
    \.csv$
    """,
    re.VERBOSE
)


def parse_race_meta_from_filename(filename: str) -> dict:
    """
    ファイル名を唯一の情報源としてレースメタ情報を取得する
    """

    name = Path(filename).name
    m = RACE_FILENAME_PATTERN.match(name)

    if not m:
        raise ValueError(f"未対応のファイル名形式です: {filename}")

    return {
        "race_id": m.group("race_id"),
        "course": m.group("course"),
        "surface": m.group("surface"),
        "distance": int(m.group("distance")),
        "field_size": (
            int(m.group("field_size"))
            if m.group("field_size") is not None
            else None
        ),
        "stage": m.group("stage"),
    }
