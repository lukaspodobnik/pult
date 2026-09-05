from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static

from schooltools_tui.progress.queries import (
    SequenceProgressSummary,
    SubjectProgressSummary,
)
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.school.subject import Subject
from schooltools_tui.widgets.lesson_progress_bar import LessonProgressBar


class SequenceProgressBlock(Vertical):
    def __init__(self, summary: SequenceProgressSummary) -> None:
        classes = (
            "sequence-progress active"
            if summary.is_active
            else "sequence-progress"
        )
        super().__init__(classes=classes)
        self.summary = summary

    def compose(self) -> ComposeResult:
        active_marker = "● " if self.summary.is_active else ""
        with Horizontal(classes="progress-heading"):
            yield Static(
                f"{active_marker}{self.summary.curriculum_section_id} · "
                f"{self.summary.title}",
                classes="progress-title",
            )
            yield Static(self._progress_label, classes="progress-count")

        yield LessonProgressBar(
            self.summary.completed_lesson_count,
            self.summary.skipped_lesson_count,
            self.summary.total_lesson_count,
        )

        if self.summary.total_lesson_count == 0:
            yield Static(
                "Noch nicht ausgefüllt",
                classes="empty-sequence-hint",
            )

    @property
    def _progress_label(self) -> str:
        return (
            f"{self.summary.progressed_lesson_count} / "
            f"{self.summary.total_lesson_count}"
        )


class SubjectProgressBlock(Vertical):
    def __init__(
        self,
        subject: Subject,
        summary: SubjectProgressSummary,
    ) -> None:
        super().__init__(classes="subject-progress")
        self.subject = subject
        self.summary = summary

    def compose(self) -> ComposeResult:
        yield Static(self.subject.name.upper(), classes="subject-title")
        yield from self._compose_next_lesson()

        with Horizontal(classes="progress-heading subject-progress-heading"):
            yield Static("Gesamt", classes="progress-title")
            yield Static(
                f"{self.summary.progressed_lesson_count} / "
                f"{self.summary.total_lesson_count}",
                classes="progress-count",
            )

        yield LessonProgressBar(
            self.summary.completed_lesson_count,
            self.summary.skipped_lesson_count,
            self.summary.total_lesson_count,
            classes="subject-progress-bar",
        )

        for sequence in self.summary.sequences:
            yield SequenceProgressBlock(sequence)

    def _compose_next_lesson(self) -> ComposeResult:
        yield Static("Nächste Stunde", classes="next-lesson-label")
        planned_lesson = self.summary.next_planned_lesson
        if planned_lesson is None:
            yield Static(
                "Keine offene geplante Stunde",
                classes="next-lesson-empty",
            )
            return

        sequence = next(
            sequence
            for sequence in self.summary.sequences
            if sequence.sequence_id == planned_lesson.sequence_id
        )
        lesson_title = planned_lesson.lesson.title or "Noch ohne Titel"
        yield Static(
            f"{sequence.curriculum_section_id} · {lesson_title}",
            classes="next-lesson-title",
        )
        yield Static(
            f"{planned_lesson.date:%d.%m.%Y} · "
            f"{planned_lesson.period}. Stunde",
            classes="next-lesson-date",
        )

        if planned_lesson.lesson.tasks:
            yield Static(
                "Aufgaben: " + " · ".join(planned_lesson.lesson.tasks),
                classes="next-lesson-details",
            )
        if planned_lesson.lesson.notes:
            yield Static(
                f"Notizen: {planned_lesson.lesson.notes}",
                classes="next-lesson-details",
            )


class SchoolClassView(Vertical):
    def __init__(
        self,
        school_class: SchoolClass,
        subjects: list[Subject],
        progress_summaries: tuple[SubjectProgressSummary, ...],
    ) -> None:
        super().__init__()
        self.school_class = school_class
        self.subjects_by_id = {subject.id: subject for subject in subjects}
        self.progress_summaries = progress_summaries

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="school-class-content"):
            yield Static(self.school_class.id, id="school-class-title")
            for summary in self.progress_summaries:
                yield SubjectProgressBlock(
                    self.subjects_by_id[summary.subject_id],
                    summary,
                )
