from dataclasses import replace
from datetime import date, time

import pytest

from pult.school.assessment import Assessment, AssessmentKind


def assessment(**changes):
    base = Assessment(
        id="bmt-8",
        subject_id="mathematik",
        kind=AssessmentKind.YEAR_GROUP_TEST,
        title="BMT 8",
        date=date(2026, 10, 1),
        start=time(8, 0),
        duration_minutes=45,
    )
    return replace(base, **changes)


@pytest.mark.parametrize("minutes,periods", [(20, (2,)), (60, (2, 3)), (45, ())])
def test_duration_does_not_determine_occupied_periods(minutes, periods):
    entry = assessment(duration_minutes=minutes, occupied_periods=periods)
    assert entry.duration_minutes == minutes
    assert entry.occupied_periods == periods


@pytest.mark.parametrize(
    "changes",
    [
        {"duration_minutes": 0},
        {"duration_minutes": True},
        {"occupied_periods": (2, 2)},
        {"occupied_periods": (0,)},
        {"occupied_periods": (True,)},
        {"group_id": " "},
    ],
)
def test_invalid_time_consumption_and_group_are_rejected(changes):
    with pytest.raises(ValueError):
        assessment(**changes)


def test_linked_tests_remain_separate_appointments():
    bmt = assessment(group_id="sa-1")
    follow_up = assessment(
        id="test-1",
        date=date(2026, 10, 15),
        kind=AssessmentKind.ANNOUNCED_TEST,
        group_id="sa-1",
    )
    assert bmt.group_id == follow_up.group_id
    assert bmt.id != follow_up.id
    assert bmt.date != follow_up.date
