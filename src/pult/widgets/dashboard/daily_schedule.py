import logging
from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from pult.curriculum.sequence import Sequence
from pult.presentation import ACTION_ICONS, UNTITLED_LESSON, WEEKDAY_NAMES
from pult.progress.class_progress import TeachingAction
from pult.progress.queries import (
    DailyScheduleSummary,
    DailyTimetableEntry,
    get_time_highlighted_occurrence,
)
from pult.school.period import Period
from pult.school.subject import Subject
from pult.widgets.capped_text import CappedText
from pult.widgets.scrolling import Horizontal, Vertical, VerticalScroll

logger = logging.getLogger(__name__)


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

    def on_mount(self) -> None:
        logger.debug(
            "daily_row_mounted occurrence=%s highlighted=%s",
            self.occurrence,
            self.has_class("time-highlighted"),
        )

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
        logger.debug("daily_row_updated previous=%s", self.occurrence)
        self.daily_entry = daily_entry
        self.subjects_by_id = subjects_by_id
        self.sequences_by_key = sequences_by_key
        for action in TeachingAction:
            self.set_class(daily_entry.action == action, action.value)
        self.set_time_highlight(daily_entry.is_time_highlighted, reason="data")
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

    def set_time_highlight(self, highlighted: bool, *, reason: str) -> None:
        changed = self.has_class("time-highlighted") != highlighted
        self.set_class(highlighted, "time-highlighted")
        if changed:
            logger.debug(
                "daily_highlight_changed occurrence=%s highlighted=%s reason=%s",
                self.occurrence,
                highlighted,
                reason,
            )
            if self.is_mounted:
                # Transparente Textfelder können noch die zuvor gezeichnete
                # Hintergrundfarbe enthalten, obwohl die Zeilenklasse stimmt.
                self.call_after_refresh(self.redraw_contents, f"highlight_{reason}")
                if logger.isEnabledFor(logging.DEBUG):
                    self.call_after_refresh(self.log_highlight_layout)

    def redraw_contents(self, reason: str) -> None:
        """Vererbte Farben und Zeichen-Caches der Zeile samt Textfeldern erneuern."""
        if not self.is_mounted:
            return
        logger.debug(
            "daily_row_redraw_requested occurrence=%s reason=%s",
            self.occurrence,
            reason,
        )
        # Ein Repaint allein kann den berechneten VisualStyle der Textfelder
        # wiederverwenden. Nach Änderungen an Vorfahren (z. B. der Startblende)
        # auch diesen Stil über Textuals öffentliche CSS-Aktualisierung erneuern.
        self.update_node_styles(animate=False)
        for widget in self.walk_children(Widget, with_self=True):
            widget.refresh(repaint=True)

    def log_highlight_layout(self) -> None:
        if self.is_mounted:
            logger.debug(
                "daily_highlight_layout occurrence=%s highlighted=%s region=%s background=%s",
                self.occurrence,
                self.has_class("time-highlighted"),
                self.region,
                self.styles.background.hex,
            )

    def _get_lesson_title(self) -> str | None:
        if self.daily_entry.assessment is not None:
            return self.daily_entry.assessment.label
        if self.daily_entry.planned_lesson is not None:
            return self.daily_entry.planned_lesson.lesson.title or UNTITLED_LESSON

        log_entry = self.daily_entry.log_entry
        if log_entry is not None and log_entry.action is TeachingAction.OTHER:
            return log_entry.comment
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
            empty.display = (
                not daily_schedule.timetable_entries
                and not daily_schedule.external_assessments
            )
            yield empty
            for entry in daily_schedule.timetable_entries:
                yield DailyScheduleRow(
                    entry,
                    self.subjects_by_id,
                    self.sequences_by_key,
                )

            yield Static(
                self._external_text(),
                classes="daily-external-assessments",
                markup=False,
            )

    def _external_text(self) -> str:
        return "\n".join(
            f"{'✓' if item.assessment.completed_on else ' '} {item.assessment.start:%H:%M} · {item.school_class_id} · {item.label} (extern)"
            for item in self.daily_schedule.external_assessments
        )

    def redraw_rows(self, reason: str) -> None:
        for row in self.query(DailyScheduleRow):
            row.redraw_contents(reason)

    async def update_data(
        self,
        daily_schedule: DailyScheduleSummary,
        subjects_by_id: dict[str, Subject],
        sequences_by_key: dict[tuple[int, str, str], Sequence],
    ) -> None:
        """Verwende Tageszeilen wieder und passe nur deren Anzahl an."""
        changed_day = self.daily_schedule.date != daily_schedule.date
        logger.debug(
            "daily_schedule_updated date=%s changed_day=%s rows=%s",
            daily_schedule.date,
            changed_day,
            len(daily_schedule.timetable_entries),
        )
        self.daily_schedule = daily_schedule
        self.subjects_by_id = subjects_by_id
        self.sequences_by_key = sequences_by_key
        self.border_title = (
            f"HEUTE · {WEEKDAY_NAMES[daily_schedule.date.weekday()].upper()}"
        )
        content = self.query_one("#daily-schedule-entries", VerticalScroll)
        self.query_one(".dashboard-empty").display = (
            not daily_schedule.timetable_entries
            and not daily_schedule.external_assessments
        )
        self.query_one(".daily-external-assessments", Static).update(
            self._external_text()
        )
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
                before=self.query_one(".daily-external-assessments"),
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
            row.set_time_highlight(
                row.occurrence == highlighted_occurrence,
                reason="clock",
            )
