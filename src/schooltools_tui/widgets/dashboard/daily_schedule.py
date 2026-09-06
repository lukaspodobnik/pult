from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static

from schooltools_tui.curriculum.sequence import Sequence
from schooltools_tui.presentation import UNTITLED_LESSON, WEEKDAY_NAMES
from schooltools_tui.progress.class_progress import TeachingAction
from schooltools_tui.progress.queries import (
    DailyAdditionalEntry,
    DailyScheduleSummary,
    DailyTimetableEntry,
    get_time_highlighted_occurrence,
)
from schooltools_tui.school.period import Period
from schooltools_tui.school.subject import Subject

ACTION_ICONS = {
    TeachingAction.COMPLETED: "✓",
    TeachingAction.CONTINUED: "↻",
    TeachingAction.CANCELLED: "×",
}


class DailyScheduleRow(Horizontal):
    def __init__(
        self,
        daily_entry: DailyTimetableEntry,
        subjects_by_id: dict[str, Subject],
        sequences_by_key: dict[tuple[int, str, str], Sequence],
    ) -> None:
        action = daily_entry.action
        classes = "daily-schedule-row"
        if action is not None:
            classes += f" {action.value}"
        if daily_entry.is_time_highlighted:
            classes += " time-highlighted"
        super().__init__(classes=classes)
        self.daily_entry = daily_entry
        self.subjects_by_id = subjects_by_id
        self.sequences_by_key = sequences_by_key

    @property
    def occurrence(self) -> tuple[str, str, int]:
        entry = self.daily_entry.timetable_entry
        return entry.school_class_id, entry.subject_id, entry.period

    def compose(self) -> ComposeResult:
        entry = self.daily_entry.timetable_entry
        yield Static(
            ACTION_ICONS.get(self.daily_entry.action, " ")
            if self.daily_entry.action is not None
            else " ",
            classes="day-status",
        )
        yield Static(f"{entry.period}.", classes="day-period")
        with Vertical(classes="day-entry-content"):
            yield Static(
                f"{entry.school_class_id} · "
                f"{self.subjects_by_id[entry.subject_id].short_name}",
                classes="day-entry-heading",
            )
            lesson_title = self._get_lesson_title()
            if lesson_title is not None:
                yield Static(lesson_title, classes="day-entry-lesson")

    def _get_lesson_title(self) -> str | None:
        if self.daily_entry.planned_lesson is not None:
            return self.daily_entry.planned_lesson.lesson.title or UNTITLED_LESSON

        log_entry = self.daily_entry.log_entry
        if log_entry is None or log_entry.lesson_id is None:
            return None

        sequence = self.sequences_by_key[
            (
                self.daily_entry.grade_level,
                log_entry.subject_id,
                log_entry.sequence_id,
            )
        ]
        lesson = next(
            lesson for lesson in sequence.lessons if lesson.id == log_entry.lesson_id
        )
        return lesson.title or UNTITLED_LESSON


class DailyAdditionalRow(Horizontal):
    def __init__(
        self,
        entry: DailyAdditionalEntry,
        subjects_by_id: dict[str, Subject],
    ) -> None:
        super().__init__(classes="daily-additional-row")
        self.entry = entry
        self.subjects_by_id = subjects_by_id

    def compose(self) -> ComposeResult:
        yield Static("+", classes="day-status")
        with Vertical(classes="day-entry-content"):
            yield Static(
                f"{self.entry.school_class_id} · "
                f"{self.subjects_by_id[self.entry.log_entry.subject_id].short_name} "
                "· Zusatzunterricht",
                classes="day-entry-heading",
            )
            if self.entry.log_entry.comment:
                yield Static(
                    self.entry.log_entry.comment,
                    classes="day-entry-lesson",
                )


class DailySchedulePanel(Vertical):
    """Zeige heutige Termine und markiere die zeitlich nächste Stunde."""

    def __init__(
        self,
        daily_schedule: DailyScheduleSummary,
        subjects_by_id: dict[str, Subject],
        sequences_by_key: dict[tuple[int, str, str], Sequence],
    ) -> None:
        super().__init__(id="daily-schedule", classes="dashboard-panel")
        self.daily_schedule = daily_schedule
        self.subjects_by_id = subjects_by_id
        self.sequences_by_key = sequences_by_key

    def compose(self) -> ComposeResult:
        daily_schedule = self.daily_schedule
        yield Static(
            f"HEUTE · {WEEKDAY_NAMES[daily_schedule.date.weekday()].upper()}",
            classes="dashboard-heading",
        )
        with VerticalScroll(id="daily-schedule-entries"):
            if not daily_schedule.timetable_entries:
                yield Static(
                    "Heute ist kein Unterricht geplant.",
                    classes="dashboard-empty",
                )
            for entry in daily_schedule.timetable_entries:
                yield DailyScheduleRow(
                    entry,
                    self.subjects_by_id,
                    self.sequences_by_key,
                )

            if daily_schedule.additional_entries:
                yield Static(
                    "WEITERE EINTRÄGE",
                    classes="daily-additional-heading",
                )
                for entry in daily_schedule.additional_entries:
                    yield DailyAdditionalRow(entry, self.subjects_by_id)

    def refresh_time_highlight(
        self, periods: list[Period], current_datetime: datetime
    ) -> None:
        """Aktualisiere die Zeitmarkierung, ohne die Tageszeilen neu aufzubauen."""
        highlighted_occurrence = get_time_highlighted_occurrence(
            [entry.timetable_entry for entry in self.daily_schedule.timetable_entries],
            periods,
            current_datetime,
        )
        for row in self.query(DailyScheduleRow):
            row.set_class(
                row.occurrence == highlighted_occurrence,
                "time-highlighted",
            )
