from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static

from schooltools_tui.curriculum.sequence import Sequence
from schooltools_tui.progress.class_progress import (
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
)
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.school.subject import Subject

WEEKDAY_NAMES = (
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
)

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
        weekday = WEEKDAY_NAMES[self.entry.date.weekday()]
        occurrence = (
            f"{self.entry.period}. Stunde"
            if self.entry.period is not None
            else ORIGIN_LABELS[self.entry.origin]
        )
        with Horizontal(classes="teaching-log-date-row"):
            yield Static(
                f"{weekday}, {self.entry.date:%d.%m.%Y}",
                classes="teaching-log-date",
            )
            yield Static(occurrence, classes="teaching-log-period")

        yield Static(
            f"{self.subject.name} · {self.sequence.curriculum_section_id} · "
            f"{self.sequence.title}",
            classes="teaching-log-sequence",
        )

        lesson_title = self._get_lesson_title()
        if lesson_title is not None:
            yield Static(lesson_title, classes="teaching-log-lesson")

        yield Static(
            f"{ACTION_LABELS[self.entry.action]} · "
            f"{ORIGIN_LABELS[self.entry.origin]}",
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
        return lesson.title or "Lesson ohne Titel"


class TeachingLogView(VerticalScroll):
    def __init__(
        self,
        school_class: SchoolClass,
        entries: tuple[TeachingLogEntry, ...],
        subjects: list[Subject],
        sequences: list[Sequence],
        *,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.school_class = school_class
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
        yield Static(
            f"Unterrichtsprotokoll · {self.school_class.id}",
            classes="teaching-log-title",
        )

        if not self.entries:
            yield Static(
                "Für diese Klasse gibt es noch keine Protokolleinträge.",
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
