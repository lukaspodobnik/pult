from textual.app import ComposeResult
from textual.widgets import Rule, Static

from pult.presentation import (
    NO_NEXT_LESSON,
    UNTITLED_LESSON,
    format_date,
)
from pult.progress.queries import (
    SequenceProgressSummary,
    SubjectProgressSummary,
)
from pult.school.school_class import SchoolClass
from pult.school.subject import Subject
from pult.widgets.lesson_progress_bar import LessonProgressBar
from pult.widgets.scrolling import Horizontal, Vertical, VerticalScroll


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
        with Vertical(classes="subject-overview"):
            yield Static(self._total_label, classes="total-label")
            yield LessonProgressBar(
                self.summary.completed_lesson_count,
                self.summary.skipped_lesson_count,
                self.summary.total_lesson_count,
                classes="subject-progress-bar",
            )
        with Horizontal(classes="class-dashboard"):
            with Vertical(classes="class-details"):
                sequences = VerticalScroll(classes="sequence-list")
                sequences.border_title = "SEQUENZEN"
                sequences.can_focus = False
                with sequences:
                    for sequence in self.summary.sequences:
                        yield SequenceProgressBlock(sequence)
                capacity = Vertical(classes="lesson-capacity")
                capacity.border_title = "STUNDENBILANZ"
                with capacity:
                    with Vertical(classes="capacity-summary"):
                        yield from self._compose_capacity()
            next_lesson = VerticalScroll(classes="class-next-lesson")
            next_lesson.border_title = "NÄCHSTE STUNDE"
            next_lesson.can_focus = False
            with next_lesson:
                yield from self._compose_next_lesson()

    @property
    def _total_label(self) -> str:
        return (
            f"{self.summary.completed_lesson_count} abgeschlossen · "
            f"{self.summary.skipped_lesson_count} übersprungen · "
            f"{self.summary.total_lesson_count} gesamt"
        )

    def _compose_capacity(self) -> ComposeResult:
        balance = self.summary.lesson_balance
        balance_class = (
            "positive" if balance > 0 else "negative" if balance < 0 else "neutral"
        )
        for label, value, classes in (
            (
                "Noch benötigt",
                str(self.summary.remaining_lesson_count),
                "remaining-lessons",
            ),
            (
                "Verfügbar",
                str(self.summary.available_period_count),
                "available-periods",
            ),
            ("Differenz", f"{balance:+d}", f"lesson-balance {balance_class}"),
        ):
            row_classes = "capacity-row"
            if classes.startswith("lesson-balance"):
                row_classes += " capacity-result"
            with Horizontal(classes=row_classes):
                yield Static(label, classes="capacity-label")
                yield Static(value, classes=f"capacity-value {classes}")
            if classes == "available-periods":
                yield Rule(classes="capacity-divider")

    def _compose_next_lesson(self) -> ComposeResult:
        for name, text in self._next_lesson_texts().items():
            classes = name
            if name in {"next-lesson-tasks", "next-lesson-material"}:
                classes += " next-lesson-details"
            widget = Static(text, classes=classes, markup=False)
            widget.display = bool(text)
            yield widget

    def _next_lesson_texts(self) -> dict[str, str]:
        texts: dict[str, str] = dict.fromkeys(
            (
                "next-lesson-empty",
                "next-lesson-title",
                "next-lesson-sequence",
                "next-lesson-date",
                "next-lesson-tasks",
                "next-lesson-material",
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
        texts["next-lesson-sequence"] = sequence.title
        texts["next-lesson-title"] = (
            f"{sequence.curriculum_section_id} · {lesson_title}"
        )
        texts["next-lesson-date"] = (
            f"{format_date(planned_lesson.date)} · {planned_lesson.period}. Stunde"
        )
        if planned_lesson.lesson.tasks:
            texts["next-lesson-tasks"] = (
                "Aufgaben: " + planned_lesson.lesson.task_summary
            )
        if planned_lesson.lesson.material:
            texts["next-lesson-material"] = (
                "Material: " + planned_lesson.lesson.material_summary
            )
        return texts

    async def update_data(
        self, subject: Subject, summary: SubjectProgressSummary
    ) -> None:
        """Verwende vorhandene Sequenzblöcke nach Anzeigeposition weiter."""
        if self.subject == subject and self.summary == summary:
            return
        self.subject = subject
        self.summary = summary
        for name, text in self._next_lesson_texts().items():
            widget = self.query_one(f".{name}", Static)
            widget.update(text)
            widget.display = bool(text)
        self.query_one(".total-label", Static).update(self._total_label)
        self.query_one(".remaining-lessons", Static).update(
            str(summary.remaining_lesson_count)
        )
        self.query_one(".subject-progress-bar", LessonProgressBar).update_counts(
            summary.completed_lesson_count,
            summary.skipped_lesson_count,
            summary.total_lesson_count,
        )
        self.query_one(".available-periods", Static).update(
            str(summary.available_period_count)
        )
        balance = self.query_one(".lesson-balance", Static)
        balance.update(f"{summary.lesson_balance:+d}")
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
            await self.query_one(".sequence-list").mount(
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
        changed_selection = self.school_class.id != school_class.id or tuple(
            s.subject_id for s in self.progress_summaries
        ) != tuple(s.subject_id for s in progress_summaries)
        self.school_class = school_class
        self.subjects_by_id = subjects_by_id
        self.progress_summaries = progress_summaries
        content = self.query_one("#school-class-content", VerticalScroll)
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
        if changed_selection:
            content.scroll_home(animate=False)
            for panel in self.query(VerticalScroll):
                panel.scroll_home(animate=False)
        self._update_titles()

    def on_mount(self) -> None:
        self._update_titles()

    def _update_titles(self) -> None:
        for block in self.query(SubjectProgressBlock):
            block.query_one(
                ".subject-overview"
            ).border_title = f"{self.school_class.id} · {block.subject.name}"

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="school-class-content"):
            for summary in self.progress_summaries:
                yield SubjectProgressBlock(
                    self.subjects_by_id[summary.subject_id],
                    summary,
                )
