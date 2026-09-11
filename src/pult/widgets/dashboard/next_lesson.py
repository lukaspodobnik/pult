from datetime import date

from textual.app import ComposeResult
from textual.widgets import Static

from pult.curriculum.sequence import Sequence
from pult.presentation import (
    NEXT_LESSON_LABEL,
    NO_NEXT_LESSON,
    UNTITLED_LESSON,
    format_date,
)
from pult.progress.queries import (
    PlannedLesson,
)
from pult.school.subject import Subject
from pult.widgets.scrolling import VerticalScroll


class NextLessonPanel(VerticalScroll, can_focus=False):
    """Zeige die nächste geplante Lesson und ihren Termin."""

    def __init__(
        self,
        planned_lesson: PlannedLesson | None,
        today: date,
        subjects_by_id: dict[str, Subject],
        sequences_by_key: dict[tuple[int, str, str], Sequence],
    ) -> None:
        super().__init__(id="next-planned-lesson", classes="dashboard-panel")
        self.border_title = NEXT_LESSON_LABEL.upper()
        self.planned_lesson = planned_lesson
        self.today = today
        self.subjects_by_id = subjects_by_id
        self.sequences_by_key = sequences_by_key

    def compose(self) -> ComposeResult:
        for name, text in self._texts().items():
            if name == "next-lesson-occurrence":
                yield Static(classes="next-lesson-spacer")
            widget = Static(text, classes=name, markup=False)
            widget.display = bool(text)
            yield widget

    def update_data(
        self,
        planned_lesson: PlannedLesson | None,
        today: date,
        subjects_by_id: dict[str, Subject],
        sequences_by_key: dict[tuple[int, str, str], Sequence],
    ) -> None:
        """Aktualisiere die festen Textfelder einschließlich des Leerzustands."""
        self.planned_lesson = planned_lesson
        self.today = today
        self.subjects_by_id = subjects_by_id
        self.sequences_by_key = sequences_by_key
        for name, text in self._texts().items():
            widget = self.query_one(f".{name}", Static)
            widget.update(text)
            widget.display = bool(text)

    def _texts(self) -> dict[str, str]:
        texts: dict[str, str] = dict.fromkeys(
            (
                "dashboard-empty",
                "next-lesson-heading",
                "next-lesson-sequence",
                "next-lesson-name",
                "next-lesson-tasks",
                "next-lesson-occurrence",
            ),
            "",
        )
        planned_lesson = self.planned_lesson
        if planned_lesson is None:
            texts["dashboard-empty"] = NO_NEXT_LESSON
            return texts

        subject = self.subjects_by_id[planned_lesson.subject_id]
        sequence = self._get_sequence(planned_lesson)
        texts["next-lesson-heading"] = (
            f"{planned_lesson.school_class_id} · {subject.name}"
        )
        texts["next-lesson-sequence"] = f"{sequence.title}"
        texts["next-lesson-name"] = planned_lesson.lesson.title or UNTITLED_LESSON
        texts["next-lesson-occurrence"] = self._format_planned_occurrence(
            planned_lesson
        )
        if planned_lesson.lesson.tasks:
            texts["next-lesson-tasks"] = (
                "Aufgaben: " + planned_lesson.lesson.task_summary
            )
        return texts

    def _get_sequence(self, planned_lesson: PlannedLesson) -> Sequence:
        return self.sequences_by_key[
            (
                planned_lesson.grade_level,
                planned_lesson.subject_id,
                planned_lesson.sequence_id,
            )
        ]

    def _format_planned_occurrence(self, planned_lesson: PlannedLesson) -> str:
        occurrence = (
            f"{format_date(planned_lesson.date, with_weekday=True)} · "
            f"{planned_lesson.period}. Stunde"
        )
        today = self.today
        if planned_lesson.date < today:
            days = (today - planned_lesson.date).days
            occurrence += f" · seit {days} Tag{'en' if days != 1 else ''} ausstehend"
        return occurrence
