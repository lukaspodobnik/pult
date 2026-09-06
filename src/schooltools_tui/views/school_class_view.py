from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static

from schooltools_tui.presentation import (
    NEXT_LESSON_LABEL,
    NO_NEXT_LESSON,
    UNTITLED_LESSON,
    format_date,
)
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
            "sequence-progress active" if summary.is_active else "sequence-progress"
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

        hint = Static("Noch nicht ausgefüllt", classes="empty-sequence-hint")
        hint.display = self.summary.total_lesson_count == 0
        yield hint

    def update_data(self, summary: SequenceProgressSummary) -> None:
        """Aktualisiere Titel, Markierung und Balken ohne neue Widgets."""
        if self.summary == summary:
            return
        self.summary = summary
        self.set_class(summary.is_active, "active")
        marker = "● " if summary.is_active else ""
        self.query_one(".progress-title", Static).update(
            f"{marker}{summary.curriculum_section_id} · {summary.title}"
        )
        self.query_one(".progress-count", Static).update(self._progress_label)
        self.query_one(LessonProgressBar).update_counts(
            summary.completed_lesson_count,
            summary.skipped_lesson_count,
            summary.total_lesson_count,
        )
        self.query_one(".empty-sequence-hint").display = summary.total_lesson_count == 0

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

        balance = self.summary.lesson_balance
        balance_class = (
            "positive" if balance > 0 else "negative" if balance < 0 else "neutral"
        )
        period_label = (
            "Stunde" if self.summary.available_period_count == 1 else "Stunden"
        )
        with Horizontal(classes="lesson-capacity"):
            yield Static(
                f"Verfügbar: {self.summary.available_period_count} {period_label}",
                classes="available-periods",
            )
            yield Static(
                f"Differenz: {balance:+d}",
                classes=f"lesson-balance {balance_class}",
            )

        for sequence in self.summary.sequences:
            yield SequenceProgressBlock(sequence)

    def _compose_next_lesson(self) -> ComposeResult:
        yield Static(NEXT_LESSON_LABEL, classes="next-lesson-label")
        for name, text in self._next_lesson_texts().items():
            classes = name
            if name in {"next-lesson-tasks", "next-lesson-notes"}:
                classes += " next-lesson-details"
            widget = Static(text, classes=classes)
            widget.display = bool(text)
            yield widget

    def _next_lesson_texts(self) -> dict[str, str]:
        texts: dict[str, str] = dict.fromkeys(
            (
                "next-lesson-empty",
                "next-lesson-title",
                "next-lesson-date",
                "next-lesson-tasks",
                "next-lesson-notes",
            ),
            "",
        )
        planned_lesson = self.summary.next_planned_lesson
        if planned_lesson is None:
            texts["next-lesson-empty"] = NO_NEXT_LESSON
            return texts

        sequence = next(
            sequence
            for sequence in self.summary.sequences
            if sequence.sequence_id == planned_lesson.sequence_id
        )
        lesson_title = planned_lesson.lesson.title or UNTITLED_LESSON
        texts["next-lesson-title"] = (
            f"{sequence.curriculum_section_id} · {lesson_title}"
        )
        texts["next-lesson-date"] = (
            f"{format_date(planned_lesson.date)} · {planned_lesson.period}. Stunde"
        )
        if planned_lesson.lesson.tasks:
            texts["next-lesson-tasks"] = "Aufgaben: " + " · ".join(
                planned_lesson.lesson.tasks
            )
        if planned_lesson.lesson.notes:
            texts["next-lesson-notes"] = f"Notizen: {planned_lesson.lesson.notes}"
        return texts

    async def update_data(
        self, subject: Subject, summary: SubjectProgressSummary
    ) -> None:
        """Verwende vorhandene Sequenzblöcke nach Anzeigeposition weiter."""
        if self.subject == subject and self.summary == summary:
            return
        self.subject = subject
        self.summary = summary
        self.query_one(".subject-title", Static).update(subject.name.upper())
        for name, text in self._next_lesson_texts().items():
            widget = self.query_one(f".{name}", Static)
            widget.update(text)
            widget.display = bool(text)
        self.query_one(".subject-progress-heading .progress-count", Static).update(
            f"{summary.progressed_lesson_count} / {summary.total_lesson_count}"
        )
        self.query_one(".subject-progress-bar", LessonProgressBar).update_counts(
            summary.completed_lesson_count,
            summary.skipped_lesson_count,
            summary.total_lesson_count,
        )
        count = summary.available_period_count
        self.query_one(".available-periods", Static).update(
            f"Verfügbar: {count} {'Stunde' if count == 1 else 'Stunden'}"
        )
        balance = self.query_one(".lesson-balance", Static)
        balance.update(f"Differenz: {summary.lesson_balance:+d}")
        for name, enabled in (
            ("positive", summary.lesson_balance > 0),
            ("negative", summary.lesson_balance < 0),
            ("neutral", summary.lesson_balance == 0),
        ):
            balance.set_class(enabled, name)
        blocks = list(self.query(SequenceProgressBlock))
        for block, sequence in zip(blocks, summary.sequences):
            block.update_data(sequence)
        for block in blocks[len(summary.sequences) :]:
            await block.remove()
        if len(summary.sequences) > len(blocks):
            await self.mount(
                *(SequenceProgressBlock(s) for s in summary.sequences[len(blocks) :])
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

    async def update_data(
        self,
        school_class: SchoolClass,
        subjects: list[Subject],
        progress_summaries: tuple[SubjectProgressSummary, ...],
    ) -> None:
        """Aktualisiere vorhandene Fachblöcke; passe nur ihre Anzahl bei Bedarf an."""
        subjects_by_id = {subject.id: subject for subject in subjects}
        if (
            self.school_class == school_class
            and self.subjects_by_id == subjects_by_id
            and self.progress_summaries == progress_summaries
        ):
            return
        changed_class = self.school_class.id != school_class.id
        self.school_class = school_class
        self.subjects_by_id = subjects_by_id
        self.progress_summaries = progress_summaries
        content = self.query_one("#school-class-content", VerticalScroll)
        self.query_one("#school-class-title", Static).update(school_class.id)
        blocks = list(content.query(SubjectProgressBlock))
        for block, summary in zip(blocks, progress_summaries):
            await block.update_data(subjects_by_id[summary.subject_id], summary)
        for block in blocks[len(progress_summaries) :]:
            await block.remove()
        if len(progress_summaries) > len(blocks):
            await content.mount(
                *(
                    SubjectProgressBlock(subjects_by_id[s.subject_id], s)
                    for s in progress_summaries[len(blocks) :]
                )
            )
        if changed_class:
            content.scroll_home(animate=False)

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="school-class-content"):
            yield Static(self.school_class.id, id="school-class-title")
            for summary in self.progress_summaries:
                yield SubjectProgressBlock(
                    self.subjects_by_id[summary.subject_id],
                    summary,
                )
