from datetime import datetime

from textual.app import ComposeResult
from textual.widgets import Static

from pult.curriculum.sequence import Sequence
from pult.presentation import UNTITLED_LESSON, WEEKDAY_NAMES
from pult.progress.class_progress import TeachingAction
from pult.progress.queries import (
    DailyAdditionalEntry,
    DailyScheduleSummary,
    DailyTimetableEntry,
    get_time_highlighted_occurrence,
)
from pult.school.period import Period
from pult.school.subject import Subject
from pult.widgets.capped_text import CappedText
from pult.widgets.scrolling import Horizontal, Vertical, VerticalScroll

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
            yield CappedText(
                f"{entry.school_class_id} · "
                f"{self.subjects_by_id[entry.subject_id].short_name}",
                classes="day-entry-heading",
            )
            lesson_title = self._get_lesson_title()
            lesson = CappedText(lesson_title or "", classes="day-entry-lesson")
            lesson.display = lesson_title is not None
            yield lesson

    def update_data(
        self,
        daily_entry: DailyTimetableEntry,
        subjects_by_id: dict[str, Subject],
        sequences_by_key: dict[tuple[int, str, str], Sequence],
    ) -> None:
        """Ersetze Daten und Status einer bestehenden Tageszeile."""
        self.daily_entry = daily_entry
        self.subjects_by_id = subjects_by_id
        self.sequences_by_key = sequences_by_key
        for action in TeachingAction:
            self.set_class(daily_entry.action == action, action.value)
        self.set_class(daily_entry.is_time_highlighted, "time-highlighted")
        entry = daily_entry.timetable_entry
        self.query_one(".day-status", Static).update(
            ACTION_ICONS.get(daily_entry.action, " ") if daily_entry.action else " "
        )
        self.query_one(".day-period", Static).update(f"{entry.period}.")
        self.query_one(".day-entry-heading", Static).update(
            f"{entry.school_class_id} · {subjects_by_id[entry.subject_id].short_name}"
        )
        title = self._get_lesson_title()
        lesson = self.query_one(".day-entry-lesson", Static)
        lesson.update(title or "")
        lesson.display = title is not None

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
            yield CappedText(
                f"{self.entry.school_class_id} · "
                f"{self.subjects_by_id[self.entry.log_entry.subject_id].short_name} "
                "· Zusatzunterricht",
                classes="day-entry-heading",
            )
            comment = CappedText(
                self.entry.log_entry.comment, classes="day-entry-lesson"
            )
            comment.display = bool(self.entry.log_entry.comment)
            yield comment

    def update_data(
        self, entry: DailyAdditionalEntry, subjects_by_id: dict[str, Subject]
    ) -> None:
        """Aktualisiere einen Zusatztermin einschließlich optionalem Kommentar."""
        self.entry = entry
        self.subjects_by_id = subjects_by_id
        self.query_one(".day-entry-heading", Static).update(
            f"{entry.school_class_id} · "
            f"{subjects_by_id[entry.log_entry.subject_id].short_name} · Zusatzunterricht"
        )
        comment = self.query_one(".day-entry-lesson", Static)
        comment.update(entry.log_entry.comment)
        comment.display = bool(entry.log_entry.comment)


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
        self.border_title = (
            f"HEUTE · {WEEKDAY_NAMES[daily_schedule.date.weekday()].upper()}"
        )
        self.subjects_by_id = subjects_by_id
        self.sequences_by_key = sequences_by_key

    def compose(self) -> ComposeResult:
        daily_schedule = self.daily_schedule
        content = VerticalScroll(id="daily-schedule-entries")
        content.can_focus = False
        with content:
            empty = Static(
                "Heute ist kein Unterricht geplant.", classes="dashboard-empty"
            )
            empty.display = not daily_schedule.timetable_entries
            yield empty
            for entry in daily_schedule.timetable_entries:
                yield DailyScheduleRow(
                    entry,
                    self.subjects_by_id,
                    self.sequences_by_key,
                )

            heading = Static("WEITERE EINTRÄGE", classes="daily-additional-heading")
            heading.display = bool(daily_schedule.additional_entries)
            yield heading
            for entry in daily_schedule.additional_entries:
                yield DailyAdditionalRow(entry, self.subjects_by_id)

    async def update_data(
        self,
        daily_schedule: DailyScheduleSummary,
        subjects_by_id: dict[str, Subject],
        sequences_by_key: dict[tuple[int, str, str], Sequence],
    ) -> None:
        """Verwende Tageszeilen wieder und passe nur deren Anzahl an."""
        changed_day = self.daily_schedule.date != daily_schedule.date
        self.daily_schedule = daily_schedule
        self.subjects_by_id = subjects_by_id
        self.sequences_by_key = sequences_by_key
        self.border_title = (
            f"HEUTE · {WEEKDAY_NAMES[daily_schedule.date.weekday()].upper()}"
        )
        content = self.query_one("#daily-schedule-entries", VerticalScroll)
        self.query_one(
            ".dashboard-empty"
        ).display = not daily_schedule.timetable_entries
        heading = self.query_one(".daily-additional-heading")
        heading.display = bool(daily_schedule.additional_entries)
        rows = list(self.query(DailyScheduleRow))
        for row, entry in zip(rows, daily_schedule.timetable_entries):
            row.update_data(entry, subjects_by_id, sequences_by_key)
        for row in rows[len(daily_schedule.timetable_entries) :]:
            await row.remove()
        if len(daily_schedule.timetable_entries) > len(rows):
            await content.mount(
                *(
                    DailyScheduleRow(e, subjects_by_id, sequences_by_key)
                    for e in daily_schedule.timetable_entries[len(rows) :]
                ),
                before=heading,
            )
        additional_rows = list(self.query(DailyAdditionalRow))
        for row, entry in zip(additional_rows, daily_schedule.additional_entries):
            row.update_data(entry, subjects_by_id)
        for row in additional_rows[len(daily_schedule.additional_entries) :]:
            await row.remove()
        if len(daily_schedule.additional_entries) > len(additional_rows):
            await content.mount(
                *(
                    DailyAdditionalRow(e, subjects_by_id)
                    for e in daily_schedule.additional_entries[len(additional_rows) :]
                )
            )
        if changed_day:
            content.scroll_home(animate=False)

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
