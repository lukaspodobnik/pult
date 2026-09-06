from datetime import date

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from schooltools_tui.curriculum.sequence import Sequence
from schooltools_tui.progress.queries import (
    PlannedLesson,
)
from schooltools_tui.school.subject import Subject

from .labels import WEEKDAY_NAMES


class NextLessonPanel(Vertical):
    """Zeige die nächste geplante Lesson und ihren Termin."""

    def __init__(
        self,
        planned_lesson: PlannedLesson | None,
        today: date,
        subjects_by_id: dict[str, Subject],
        sequences_by_key: dict[tuple[int, str, str], Sequence],
    ) -> None:
        super().__init__(id="next-planned-lesson", classes="dashboard-panel")
        self.planned_lesson = planned_lesson
        self.today = today
        self.subjects_by_id = subjects_by_id
        self.sequences_by_key = sequences_by_key

    def compose(self) -> ComposeResult:
        yield Static("NÄCHSTE GEPLANTE LESSON", classes="dashboard-heading")
        planned_lesson = self.planned_lesson
        if planned_lesson is None:
            yield Static(
                "Keine offene geplante Lesson",
                classes="dashboard-empty",
            )
            return

        subject = self.subjects_by_id[planned_lesson.subject_id]
        sequence = self._get_sequence(planned_lesson)
        yield Static(
            f"{planned_lesson.school_class_id} · {subject.name}",
            classes="next-lesson-heading",
        )
        yield Static(
            f"{sequence.curriculum_section_id} · {sequence.title}",
            classes="next-lesson-sequence",
        )
        yield Static(
            planned_lesson.lesson.title or "Lesson ohne Titel",
            classes="next-lesson-name",
        )
        yield Static(
            self._format_planned_occurrence(planned_lesson),
            classes="next-lesson-occurrence",
        )

    def _get_sequence(self, planned_lesson: PlannedLesson) -> Sequence:
        return self.sequences_by_key[
            (
                planned_lesson.grade_level,
                planned_lesson.subject_id,
                planned_lesson.sequence_id,
            )
        ]

    def _format_planned_occurrence(self, planned_lesson: PlannedLesson) -> str:
        weekday = WEEKDAY_NAMES[planned_lesson.date.weekday()]
        occurrence = (
            f"{weekday}, {planned_lesson.date:%d.%m.%Y} · "
            f"{planned_lesson.period}. Stunde"
        )
        today = self.today
        if planned_lesson.date < today:
            days = (today - planned_lesson.date).days
            occurrence += f" · seit {days} Tag{'en' if days != 1 else ''} ausstehend"
        return occurrence
