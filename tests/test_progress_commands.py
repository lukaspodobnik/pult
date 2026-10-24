from datetime import date

import pytest

from pult.curriculum.sequence import Lesson, Sequence
from pult.progress.class_progress import (
    ActiveSequence,
    ClassProgress,
    TeachingAction,
    TeachingOrigin,
)
from pult.progress.commands import (
    LessonCompletionState,
    ProgressCommandError,
    add_extra_lesson,
    cancel_scheduled_lesson,
    complete_additional_lesson,
    complete_lesson,
    continue_lesson,
    record_spontaneous_lesson,
    set_active_sequence,
    skip_lesson,
    undo_last_entry,
)
from pult.progress.queries import PlannedLesson, get_next_lesson


def test_complete_lesson_records_scheduled_completion(
    empty_progress, planned_lesson, sequences
):
    result = complete_lesson(empty_progress, planned_lesson, sequences, "Erledigt")

    entry = result.progress.entries[-1]
    assert entry.action is TeachingAction.COMPLETED
    assert entry.origin is TeachingOrigin.SCHEDULED
    assert entry.period == 1
    assert entry.comment == "Erledigt"
    assert result.state is LessonCompletionState.CONTINUES_SEQUENCE


def test_skip_progresses_lesson_without_consuming_occurrence(
    empty_progress, planned_lesson, sequences
):
    result = skip_lesson(empty_progress, planned_lesson, sequences)

    entry = result.progress.entries[-1]
    assert entry.action is TeachingAction.SKIPPED
    assert entry.origin is TeachingOrigin.NONE
    assert entry.period is None
    assert get_next_lesson(result.progress, sequences, "mathematik", 5).id == "lesson-2"


def test_continue_consumes_occurrence_but_keeps_lesson_open(
    empty_progress, planned_lesson, sequences
):
    progress = continue_lesson(
        empty_progress, planned_lesson, sequences, "  Sicherung noch offen  "
    )

    assert progress.entries[-1].action is TeachingAction.CONTINUED
    assert progress.entries[-1].comment == "Sicherung noch offen"
    assert get_next_lesson(progress, sequences, "mathematik", 5).id == "lesson-1"


@pytest.mark.parametrize("comment", ["", "   ", "\n\t"])
def test_continue_requires_reason(empty_progress, planned_lesson, sequences, comment):
    with pytest.raises(ProgressCommandError, match="Grund für die Fortsetzung"):
        continue_lesson(empty_progress, planned_lesson, sequences, comment)
    assert empty_progress.entries == ()


def test_cancel_consumes_occurrence_but_keeps_lesson_open(
    empty_progress, planned_lesson, sequences
):
    progress = cancel_scheduled_lesson(
        empty_progress, planned_lesson, sequences, "Feueralarm"
    )

    assert progress.entries[-1].action is TeachingAction.CANCELLED
    assert progress.entries[-1].comment == "Feueralarm"
    assert get_next_lesson(progress, sequences, "mathematik", 5).id == "lesson-1"


def test_extra_lesson_without_progress_keeps_next_lesson(empty_progress, sequences):
    progress = add_extra_lesson(
        empty_progress, "mathematik", date(2026, 9, 8), "Wiederholung"
    )

    assert progress.entries[-1].action is TeachingAction.OTHER
    assert progress.entries[-1].origin is TeachingOrigin.ADDITIONAL
    assert get_next_lesson(progress, sequences, "mathematik", 5).id == "lesson-1"


def test_additional_completion_progresses_lesson(empty_progress, sequences):
    result = complete_additional_lesson(
        empty_progress,
        "mathematik",
        5,
        date(2026, 9, 8),
        sequences,
    )

    entry = result.progress.entries[-1]
    assert entry.action is TeachingAction.COMPLETED
    assert entry.origin is TeachingOrigin.ADDITIONAL
    assert entry.period is None
    assert get_next_lesson(result.progress, sequences, "mathematik", 5).id == "lesson-2"


def test_last_lesson_requests_next_sequence(empty_progress, planned_lesson, sequences):
    first = complete_lesson(empty_progress, planned_lesson, sequences).progress
    second_plan = PlannedLesson(
        "5A",
        5,
        "mathematik",
        "sequence-1",
        sequences[0].lessons[1],
        date(2026, 9, 7),
        2,
    )

    result = complete_lesson(first, second_plan, sequences)

    assert result.state is LessonCompletionState.NEEDS_NEXT_SEQUENCE


def test_last_lesson_of_only_sequence_completes_subject(
    empty_progress, planned_lesson, sequences
):
    one_lesson = Sequence(
        "only",
        "M5 1",
        "mathematik",
        5,
        "Einzig",
        1,
        [Lesson("only-lesson", "Ende", [], "")],
    )
    progress = ClassProgress((ActiveSequence("mathematik", "only"),), ())
    plan = PlannedLesson(
        "5A",
        5,
        "mathematik",
        "only",
        one_lesson.lessons[0],
        date(2026, 9, 7),
        1,
    )

    result = complete_lesson(progress, plan, [one_lesson])

    assert result.state is LessonCompletionState.COMPLETES_SUBJECT


def test_undo_removes_last_entry_and_restores_sequence(
    empty_progress, planned_lesson, sequences
):
    completed = complete_lesson(empty_progress, planned_lesson, sequences).progress
    changed = set_active_sequence(completed, "mathematik", "sequence-2", 5, sequences)

    restored = undo_last_entry(changed)

    assert restored.entries == ()
    assert restored.active_sequences[0].sequence_id == "sequence-1"


def test_undo_rejects_empty_progress(empty_progress):
    with pytest.raises(ProgressCommandError):
        undo_last_entry(empty_progress)


def test_set_active_sequence_rejects_current_sequence(empty_progress, sequences):
    with pytest.raises(ProgressCommandError):
        set_active_sequence(empty_progress, "mathematik", "sequence-1", 5, sequences)


def test_command_rejects_stale_planned_lesson(
    empty_progress, planned_lesson, sequences
):
    progress = complete_lesson(empty_progress, planned_lesson, sequences).progress
    with pytest.raises(ProgressCommandError):
        complete_lesson(progress, planned_lesson, sequences)


def test_spontaneous_consumes_regular_slot_without_advancing_and_can_be_undone(
    empty_progress,
    planned_lesson,
    sequences,
    timetable_entries,
    school_calendar,
):
    from pult.progress.queries.scheduling import get_next_scheduled_occurrence

    progress = record_spontaneous_lesson(
        empty_progress, planned_lesson, sequences, "  Übung vor der Schulaufgabe  "
    )
    entry = progress.entries[-1]
    assert entry.action is TeachingAction.OTHER
    assert entry.origin is TeachingOrigin.SCHEDULED
    assert entry.lesson_id is None
    assert entry.comment == "Übung vor der Schulaufgabe"
    assert (entry.date, entry.period) == (planned_lesson.date, planned_lesson.period)
    assert get_next_lesson(progress, sequences, "mathematik", 5).id == "lesson-1"
    assert get_next_scheduled_occurrence(
        progress, timetable_entries, "5A", "mathematik", school_calendar, []
    ) == (date(2026, 9, 7), 2)
    with pytest.raises(ProgressCommandError):
        record_spontaneous_lesson(
            progress, planned_lesson, sequences, "Doppelte Buchung"
        )
    assert undo_last_entry(progress, subject_id="mathematik") == empty_progress


@pytest.mark.parametrize("description", ["", "   "])
def test_spontaneous_requires_description(
    empty_progress, planned_lesson, sequences, description
):
    with pytest.raises(ProgressCommandError):
        record_spontaneous_lesson(
            empty_progress, planned_lesson, sequences, description
        )
