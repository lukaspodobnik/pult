from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static

from pult.curriculum.sequence import Sequence
from pult.presentation import UNTITLED_LESSON, format_date
from pult.progress.class_progress import (
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
)
from pult.school.school_class import SchoolClass
from pult.school.subject import Subject

ACTION_LABELS = {
    TeachingAction.COMPLETED: "Abgeschlossen",
    TeachingAction.SKIPPED: "Übersprungen",
    TeachingAction.CONTINUED: "Fortgesetzt",
    TeachingAction.CANCELLED: "Ausgefallen",
    TeachingAction.OTHER: "Zusatzunterricht",
}

ORIGIN_LABELS = {
    TeachingOrigin.SCHEDULED: "Stundenplantermin",
    TeachingOrigin.ADDITIONAL: "Zusatztermin",
    TeachingOrigin.NONE: "Ohne Termin",
}


class TeachingLogEntryBlock(Vertical):
    def __init__(
        self,
        entry: TeachingLogEntry,
        subject: Subject,
        sequence: Sequence,
    ) -> None:
        super().__init__(classes=f"teaching-log-entry {entry.action.value}")
        self.entry = entry
        self.subject = subject
        self.sequence = sequence

    def compose(self) -> ComposeResult:
        occurrence = (
            f"{self.entry.period}. Stunde"
            if self.entry.period is not None
            else ORIGIN_LABELS[self.entry.origin]
        )
        with Horizontal(classes="teaching-log-date-row"):
            yield Static(
                format_date(self.entry.date, with_weekday=True),
                classes="teaching-log-date",
            )
            yield Static(occurrence, classes="teaching-log-period")

        yield Static(
            f"{self.sequence.curriculum_section_id} · {self.sequence.title}",
            classes="teaching-log-sequence",
        )

        lesson_title = self._get_lesson_title()
        if lesson_title is not None:
            yield Static(lesson_title, classes="teaching-log-lesson")

        yield Static(
            f"{ACTION_LABELS[self.entry.action]} · {ORIGIN_LABELS[self.entry.origin]}",
            classes="teaching-log-kind",
        )

        if self.entry.comment:
            yield Static(
                self.entry.comment,
                classes="teaching-log-comment",
            )

    def _get_lesson_title(self) -> str | None:
        if self.entry.lesson_id is None:
            return None

        lesson = next(
            lesson
            for lesson in self.sequence.lessons
            if lesson.id == self.entry.lesson_id
        )
        return lesson.title or UNTITLED_LESSON


class TeachingLogView(VerticalScroll):
    def __init__(
        self,
        school_class: SchoolClass,
        entries: tuple[TeachingLogEntry, ...],
        subjects: list[Subject],
        sequences: list[Sequence],
        *,
        id: str | None = None,
        subject_id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.school_class = school_class
        self.subject_id = subject_id
        self.entries = entries
        self.subjects_by_id = {subject.id: subject for subject in subjects}
        self.sequences_by_key = {
            (sequence.subject_id, sequence.id): sequence
            for sequence in sequences
            if sequence.grade_level == school_class.grade_level
        }

    def on_mount(self) -> None:
        # The entries remain chronological, while the latest one is visible first.
        self.scroll_end(animate=False)

    def compose(self) -> ComposeResult:
        if not self.entries:
            yield Static(
                "Für dieses Fach gibt es noch keine Protokolleinträge."
                if self.subject_id is not None
                else "Für diese Klasse gibt es noch keine Protokolleinträge.",
                classes="teaching-log-empty",
            )
            return

        indexed_entries = enumerate(self.entries)
        sorted_entries = sorted(
            indexed_entries,
            key=lambda item: (
                item[1].date,
                item[1].period if item[1].period is not None else 99,
                item[0],
            ),
        )
        for _, entry in sorted_entries:
            yield TeachingLogEntryBlock(
                entry,
                self.subjects_by_id[entry.subject_id],
                self.sequences_by_key[(entry.subject_id, entry.sequence_id)],
            )
