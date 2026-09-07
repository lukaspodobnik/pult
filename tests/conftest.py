from datetime import date, time

import pytest

from pult.curriculum.sequence import Lesson, Sequence
from pult.progress.class_progress import ActiveSequence, ClassProgress
from pult.progress.queries import PlannedLesson
from pult.school.calendar import Closure, ClosureKind, SchoolCalendar
from pult.school.period import Period
from pult.school.school_class import SchoolClass
from pult.school.subject import Subject
from pult.school.timetable import TimetableEntry


@pytest.fixture(autouse=True)
def isolated_omarchy_palette(tmp_path, monkeypatch):
    """Tests lesen nie die Palette des tatsächlich laufenden Desktops."""
    monkeypatch.setattr(
        "pult.services.omarchy_theme.get_omarchy_palette_path",
        lambda: tmp_path / "omarchy" / "colors.toml",
    )
    monkeypatch.setattr(
        "pult.config.app_config.LEGACY_APP_CONFIG_PATH", tmp_path / "legacy-config.toml"
    )


@pytest.fixture
def subject() -> Subject:
    return Subject("mathematik", "Mathematik", "Ma", [5])


@pytest.fixture
def school_class() -> SchoolClass:
    return SchoolClass("5A", 5, ["mathematik"])


@pytest.fixture
def sequences() -> list[Sequence]:
    return [
        Sequence(
            id="sequence-1",
            curriculum_section_id="M5 1",
            subject_id="mathematik",
            grade_level=5,
            title="Natürliche Zahlen",
            recommended_lesson_count=2,
            lessons=[
                Lesson("lesson-1", "Zahlen ordnen", ["Aufgabe 1"], ""),
                Lesson("lesson-2", "Zahlen runden", [], "Hinweis"),
            ],
        ),
        Sequence(
            id="sequence-2",
            curriculum_section_id="M5 2",
            subject_id="mathematik",
            grade_level=5,
            title="Rechenarten",
            recommended_lesson_count=1,
            lessons=[Lesson("lesson-3", "Addieren", [], "")],
        ),
    ]


@pytest.fixture
def empty_progress() -> ClassProgress:
    return ClassProgress(
        active_sequences=(ActiveSequence("mathematik", "sequence-1"),),
        entries=(),
    )


@pytest.fixture
def school_calendar() -> SchoolCalendar:
    return SchoolCalendar(
        school_year="2026-2027",
        first_school_day=date(2026, 9, 7),
        last_school_day=date(2026, 9, 18),
        closures=(
            Closure(
                "Feiertag",
                ClosureKind.PUBLIC_HOLIDAY,
                date(2026, 9, 14),
                date(2026, 9, 14),
            ),
        ),
    )


@pytest.fixture
def periods() -> list[Period]:
    return [
        Period(1, time(8, 0), time(8, 45)),
        Period(2, time(8, 50), time(9, 35)),
        Period(3, time(9, 55), time(10, 40)),
    ]


@pytest.fixture
def timetable_entries() -> list[TimetableEntry]:
    return [
        TimetableEntry("monday", 1, "5A", "mathematik", "101"),
        TimetableEntry("monday", 2, "5A", "mathematik", "101"),
        TimetableEntry("wednesday", 1, "5A", "mathematik", "101"),
    ]


@pytest.fixture
def planned_lesson(sequences: list[Sequence]) -> PlannedLesson:
    return PlannedLesson(
        school_class_id="5A",
        grade_level=5,
        subject_id="mathematik",
        sequence_id="sequence-1",
        lesson=sequences[0].lessons[0],
        date=date(2026, 9, 7),
        period=1,
    )


@pytest.fixture
def local_closure() -> Closure:
    return Closure(
        "Wandertag",
        ClosureKind.LOCAL,
        date(2026, 9, 9),
        date(2026, 9, 9),
    )
