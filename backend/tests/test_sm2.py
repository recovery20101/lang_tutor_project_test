import pytest
from datetime import datetime, timezone, timedelta
from app.services.sm2 import calculate_sm2


def test_calculate_sm2_perfect_response():
    result = calculate_sm2(score_10=10, repetitions=0, interval=0, easiness_factor=2.5)

    assert result["repetitions"] == 1
    assert result["interval"] == 1
    assert result["easiness_factor"] == 2.60
    assert result["status"] == "mastered"

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs((result["last_reviewed"] - now).total_seconds()) < 2
    assert abs((result["next_review"] - (now + timedelta(days=1))).total_seconds()) < 2


def test_calculate_sm2_bad_response():
    result = calculate_sm2(score_10=1, repetitions=5, interval=10, easiness_factor=2.5)

    assert result["repetitions"] == 0
    assert result["interval"] == 1
    assert result["status"] == "learning"
    assert result["easiness_factor"] == 1.7


def test_calculate_sm2_second_repetition():
    result = calculate_sm2(score_10=8, repetitions=1, interval=1, easiness_factor=2.5)

    assert result["repetitions"] == 2
    assert result["interval"] == 6
    assert result["status"] == "mastered"
    assert result["easiness_factor"] == 2.5


def test_calculate_sm2_ef_boundary():
    result = calculate_sm2(score_10=0, repetitions=5, interval=10, easiness_factor=1.4)

    assert result["easiness_factor"] == 1.3
    assert result["repetitions"] == 0
    assert result["interval"] == 1
    assert result["status"] == "learning"


def test_calculate_sm2_long_interval():
    result = calculate_sm2(score_10=8, repetitions=2, interval=6, easiness_factor=2.5)

    assert result["repetitions"] == 3
    assert result["interval"] == 15
    assert result["easiness_factor"] == 2.5
