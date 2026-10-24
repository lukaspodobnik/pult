from rich.table import Table
from textual.app import ComposeResult
from textual.widgets import Static

from pult.presentation import (
    NO_NEXT_LESSON,
    UNTITLED_LESSON,
    format_compact_date,
)
from pult.progress.class_progress import TeachingAction, TeachingOrigin
from pult.progress.queries import (
    SequenceProgressSummary,
    SubjectProgressSummary,
)
from pult.progress.queries.assessments import PlannedAssessment, next_event
from pult.school.school_class import SchoolClass
from pult.school.subject import Subject
from pult.views.teaching_log_view import ACTION_LABELS, ORIGIN_LABELS
from pult.widgets.capped_text import CappedText
from pult.widgets.lesson_progress_bar import LessonProgressBar
from pult.widgets.materials import render_material_list
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
        yield Static(self._held_label, classes="held-lessons", markup=False)

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
        self.query_one(".held-lessons", Static).update(self._held_label)
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

    @property
    def _held_label(self) -> str:
        return f"{self.summary.held_lesson_count} Std. gehalten"


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
                capacity.border_title = "AUSBLICK"
                with capacity:
                    with Horizontal(classes="outlook-columns"):
                        yield from self._compose_capacity()
                        with Vertical(classes="class-assessment-details"):
                            yield Static(
                                "Nächster Leistungsnachweis",
                                classes="class-assessment-label",
                            )
                            yield from self._compose_texts(self._assessment_texts())
            context = VerticalScroll(classes="class-context")
            context.can_focus = False
            with context:
                next_lesson = Vertical(classes="class-next-lesson")
                next_lesson.border_title = "NÄCHSTE STUNDE"
                with next_lesson:
                    yield from self._compose_texts(self._next_lesson_texts())
                    material = self._next_lesson_material()
                    materials = Vertical(classes="next-lesson-materials")
                    materials.display = bool(material)
                    with materials:
                        yield Static(
                            "Materialien", classes="next-lesson-material-label"
                        )
                        items = VerticalScroll(classes="next-lesson-material-list")
                        items.can_focus = False
                        with items:
                            yield Static(
                                material, classes="next-lesson-material", markup=False
                            )
                last = Vertical(classes="class-last-entry")
                last.border_title = "ZULETZT"
                with last:
                    texts = self._last_entry_texts()
                    yield from self._compose_texts(
                        {"last-entry-empty": texts.pop("last-entry-empty")}
                    )
                    metadata = Horizontal(classes="last-entry-metadata")
                    metadata.display = self.summary.last_entry is not None
                    with metadata:
                        yield from self._compose_texts(
                            {
                                name: texts.pop(name)
                                for name in ("last-entry-date", "last-entry-action")
                            }
                        )
                    yield from self._compose_texts(texts)

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
        with Vertical(classes="capacity-figure"):
            yield Static("Stundenbilanz", classes="capacity-label")
            value = Static(
                self._balance_label,
                classes=f"capacity-value lesson-balance {balance_class}",
            )
            value.tooltip = self._balance_detail
            yield value
            yield Static(self._balance_caption, classes="capacity-caption")

    @property
    def _balance_label(self) -> str:
        balance = self.summary.lesson_balance
        return f"{balance:+d} Std." if balance else "0 Std."

    @property
    def _balance_caption(self) -> str:
        balance = self.summary.lesson_balance
        return (
            "Puffer"
            if balance > 0
            else "Fehlende Zeit"
            if balance < 0
            else "Ausgeglichen"
        )

    @property
    def _balance_detail(self) -> str:
        return (
            f"Nach aktuellem Plan: {self.summary.available_period_count} Std. verfügbar, "
            f"{self.summary.remaining_lesson_count} Std. noch geplant."
        )

    @staticmethod
    def _assessment_date(item: PlannedAssessment) -> str:
        entry = item.assessment
        occurrence = (
            "/".join(map(str, sorted(entry.occupied_periods))) + ". Stunde"
            if entry.occupied_periods
            else f"{entry.start:%H:%M} Uhr · extern"
        )
        return f"{format_compact_date(entry.date)} · {occurrence}"

    def _assessment_texts(self) -> dict[str, str]:
        item = self.summary.next_assessment
        return {
            "class-assessment": f"{item.number}. {item.assessment.kind.label}"
            if item
            else "Kein Leistungsnachweis geplant",
            "class-assessment-topic": item.assessment.title if item else "",
            "class-assessment-date": self._assessment_date(item) if item else "",
        }

    def _compose_texts(self, texts: dict[str, str]) -> ComposeResult:
        line_limits = {
            "last-entry-comment": 3,
            "class-assessment": 1,
            "class-assessment-topic": 1,
            "class-assessment-date": 1,
        }
        for name, text in texts.items():
            if name == "last-entry-action":
                widget = Static(text, classes=name, markup=False)
            else:
                widget = CappedText(text, classes=name, lines=line_limits.get(name, 2))
            widget.display = bool(text)
            widget.tooltip = text or None
            yield widget

    def _next_lesson_texts(self) -> dict[str, str]:
        texts: dict[str, str] = dict.fromkeys(
            (
                "next-lesson-empty",
                "next-lesson-date",
                "next-lesson-title",
                "next-lesson-assessment-topic",
                "next-lesson-sequence",
            ),
            "",
        )
        planned_lesson = next_event(
            self.summary.next_planned_lesson, self.summary.next_scheduled_assessment
        )
        if planned_lesson is None:
            texts["next-lesson-empty"] = NO_NEXT_LESSON
            return texts

        if isinstance(planned_lesson, PlannedAssessment):
            texts["next-lesson-title"] = (
                f"{planned_lesson.number}. {planned_lesson.assessment.kind.label}"
            )
            texts["next-lesson-assessment-topic"] = planned_lesson.assessment.title
            texts["next-lesson-date"] = self._assessment_date(planned_lesson)
            return texts

        sequence = next(
            sequence
            for sequence in self.summary.sequences
            if sequence.sequence_id == planned_lesson.sequence_id
        )
        texts["next-lesson-sequence"] = (
            f"{sequence.curriculum_section_id} · {sequence.title}"
        )
        texts["next-lesson-date"] = (
            f"{format_compact_date(planned_lesson.date)} · "
            f"{planned_lesson.period}. Stunde"
        )
        texts["next-lesson-title"] = planned_lesson.lesson.title or UNTITLED_LESSON
        return texts

    def _next_lesson_material(self) -> Table | str:
        planned = next_event(
            self.summary.next_planned_lesson, self.summary.next_scheduled_assessment
        )
        if planned is None or isinstance(planned, PlannedAssessment):
            return ""
        return render_material_list(planned.lesson.material_markdown())

    def _last_entry_texts(self) -> dict[str, str]:
        texts: dict[str, str] = dict.fromkeys(
            (
                "last-entry-empty",
                "last-entry-date",
                "last-entry-action",
                "last-entry-title",
                "last-entry-sequence",
                "last-entry-comment",
            ),
            "",
        )
        last = self.summary.last_entry
        if last is None:
            texts["last-entry-empty"] = "Noch kein Protokolleintrag für dieses Fach"
            return texts
        entry = last.entry
        occurrence = (
            f"{entry.period}. Stunde"
            if entry.period is not None
            else ORIGIN_LABELS[entry.origin]
        )
        texts["last-entry-date"] = f"{format_compact_date(entry.date)} · {occurrence}"
        texts["last-entry-action"] = (
            "Spontanunterricht"
            if entry.action is TeachingAction.OTHER
            and entry.origin is TeachingOrigin.SCHEDULED
            else ACTION_LABELS[entry.action]
        )
        texts["last-entry-title"] = last.title or (
            UNTITLED_LESSON if entry.lesson_id else ""
        )
        texts["last-entry-sequence"] = last.sequence_label
        texts["last-entry-comment"] = entry.comment
        return texts

    async def update_data(
        self, subject: Subject, summary: SubjectProgressSummary
    ) -> None:
        """Verwende vorhandene Sequenzblöcke nach Anzeigeposition weiter."""
        if self.subject == subject and self.summary == summary:
            return
        self.subject = subject
        self.summary = summary
        material = self._next_lesson_material()
        self.query_one(".next-lesson-materials").display = bool(material)
        self.query_one(".next-lesson-material", Static).update(material)
        for name, text in {
            **self._assessment_texts(),
            **self._next_lesson_texts(),
            **self._last_entry_texts(),
        }.items():
            widget = self.query_one(f".{name}", Static)
            widget.update(text)
            widget.display = bool(text)
            widget.tooltip = text or None
        self.query_one(".last-entry-metadata").display = summary.last_entry is not None
        self.query_one(".total-label", Static).update(self._total_label)
        self.query_one(".subject-progress-bar", LessonProgressBar).update_counts(
            summary.completed_lesson_count,
            summary.skipped_lesson_count,
            summary.total_lesson_count,
        )
        balance = self.query_one(".lesson-balance", Static)
        balance.update(self._balance_label)
        balance.tooltip = self._balance_detail
        self.query_one(".capacity-caption", Static).update(self._balance_caption)
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
