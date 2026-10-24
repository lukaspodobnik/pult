from datetime import date

from rich.table import Table
from textual.app import ComposeResult
from textual.widgets import Static

from pult.curriculum.sequence import Sequence
from pult.presentation import (
    NEXT_LESSON_LABEL,
    NO_NEXT_LESSON,
    UNTITLED_LESSON,
    format_compact_date,
)
from pult.progress.queries import (
    PlannedLesson,
)
from pult.progress.queries.assessments import PlannedAssessment
from pult.school.subject import Subject
from pult.widgets.capped_text import CappedText
from pult.widgets.materials import render_material_list
from pult.widgets.scrolling import Horizontal, Vertical, VerticalScroll


class NextLessonPanel(VerticalScroll, can_focus=False):
    """Zeige die nächste geplante Lesson und ihren Termin."""

    def __init__(
        self,
        planned_lesson: PlannedLesson | PlannedAssessment | None,
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
        texts = self._texts()
        yield from self._compose_texts(
            {"dashboard-empty": texts.pop("dashboard-empty")}
        )
        metadata = Horizontal(classes="next-lesson-metadata")
        metadata.display = self.planned_lesson is not None
        with metadata:
            yield from self._compose_texts(
                {
                    name: texts.pop(name)
                    for name in ("next-lesson-heading", "next-lesson-occurrence")
                }
            )
        yield from self._compose_texts(texts)
        material = self._material()
        materials = Vertical(classes="next-lesson-materials")
        materials.display = bool(material)
        with materials:
            yield Static("Materialien", classes="next-lesson-material-label")
            yield Static(material, classes="next-lesson-material", markup=False)

    def _compose_texts(self, texts: dict[str, str]) -> ComposeResult:
        for name, text in texts.items():
            if name == "next-lesson-occurrence":
                widget = Static(text, classes=name, markup=False)
            else:
                widget = CappedText(text, classes=name, lines=2)
            widget.display = bool(text)
            widget.tooltip = text or None
            yield widget

    def update_data(
        self,
        planned_lesson: PlannedLesson | PlannedAssessment | None,
        today: date,
        subjects_by_id: dict[str, Subject],
        sequences_by_key: dict[tuple[int, str, str], Sequence],
    ) -> None:
        """Aktualisiere die festen Textfelder einschließlich des Leerzustands."""
        changed_lesson = self.planned_lesson != planned_lesson
        self.planned_lesson = planned_lesson
        self.today = today
        self.subjects_by_id = subjects_by_id
        self.sequences_by_key = sequences_by_key
        self.query_one(".next-lesson-metadata").display = planned_lesson is not None
        for name, text in self._texts().items():
            widget = self.query_one(f".{name}", Static)
            widget.update(text)
            widget.display = bool(text)
            widget.tooltip = text or None
        material = self._material()
        self.query_one(".next-lesson-materials").display = bool(material)
        self.query_one(".next-lesson-material", Static).update(material)
        if changed_lesson:
            self.call_after_refresh(self.scroll_home, animate=False)

    def _texts(self) -> dict[str, str]:
        texts: dict[str, str] = dict.fromkeys(
            (
                "dashboard-empty",
                "next-lesson-heading",
                "next-lesson-occurrence",
                "next-lesson-overdue",
                "next-lesson-name",
                "next-lesson-assessment-topic",
                "next-lesson-sequence",
                "next-lesson-details",
            ),
            "",
        )
        planned_lesson = self.planned_lesson
        if planned_lesson is None:
            texts["dashboard-empty"] = NO_NEXT_LESSON
            return texts

        if isinstance(planned_lesson, PlannedAssessment):
            entry = planned_lesson.assessment
            texts["next-lesson-heading"] = (
                f"{planned_lesson.school_class_id} · {self.subjects_by_id[entry.subject_id].name}"
            )
            texts["next-lesson-name"] = f"{planned_lesson.number}. {entry.kind.label}"
            texts["next-lesson-assessment-topic"] = entry.title
            texts["next-lesson-occurrence"] = (
                f"{format_compact_date(entry.date)} · {planned_lesson.period}. Stunde"
            )
            texts["next-lesson-details"] = (
                f"{entry.duration_minutes} Minuten · Belegte Stunden: "
                + ", ".join(map(str, entry.occupied_periods))
            )
            return texts

        subject = self.subjects_by_id[planned_lesson.subject_id]
        sequence = self._get_sequence(planned_lesson)
        texts["next-lesson-heading"] = (
            f"{planned_lesson.school_class_id} · {subject.name}"
        )
        texts["next-lesson-sequence"] = (
            f"{sequence.curriculum_section_id} · {sequence.title}"
        )
        texts["next-lesson-name"] = planned_lesson.lesson.title or UNTITLED_LESSON
        texts["next-lesson-occurrence"] = (
            f"{format_compact_date(planned_lesson.date)} · "
            f"{planned_lesson.period}. Stunde"
        )
        if planned_lesson.date < self.today:
            days = (self.today - planned_lesson.date).days
            texts["next-lesson-overdue"] = (
                f"Seit {days} Tag{'en' if days != 1 else ''} ausstehend"
            )
        return texts

    def _material(self) -> Table | str:
        planned = self.planned_lesson
        if planned is None or isinstance(planned, PlannedAssessment):
            return ""
        return render_material_list(planned.lesson.material_markdown())

    def _get_sequence(self, planned_lesson: PlannedLesson) -> Sequence:
        return self.sequences_by_key[
            (
                planned_lesson.grade_level,
                planned_lesson.subject_id,
                planned_lesson.sequence_id,
            )
        ]
