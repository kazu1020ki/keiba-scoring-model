import pytest

pytest.importorskip("numpy")

from scoring.score_past5 import calc_distance_reliability, calc_lead_score
from course.course_score import rebalance_weights


def test_distance_reliability_penalizes_stretch_more_than_shorten():
    target = 1800
    stretch = calc_distance_reliability(1200, target)
    shorten = calc_distance_reliability(2400, target)

    assert stretch < shorten


def test_lead_score_penalizes_big_fade():
    fade = calc_lead_score("1-1-1-12", field_size=16, pace="ミドル")
    keep = calc_lead_score("1-1-1-2", field_size=16, pace="ミドル")

    assert fade is not None and keep is not None
    assert fade < keep


def test_rebalance_weights_caps_lead_bias():
    speed, lead, closing = rebalance_weights(1.0, 2.5, 0.5)

    assert round(speed + lead + closing, 6) == 1.0
    assert lead <= 0.42
