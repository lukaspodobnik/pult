from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import Label, OptionList

from pult.curriculum.sequence import Sequence
from pult.progress.class_progress import (
    ClassProgress,
    load_class_progress,
    validate_class_progress,
)
from pult.school.school_class import SchoolClass, load_school_classes
from pult.school.subject import Subject, load_subjects
from pult.screens.base_screen import PultScreen
from pult.views.teaching_log_view import TeachingLogView
from pult.widgets.footer import PultFooter
from pult.widgets.navigation import ViewPicker


class TeachingLogScreen(PultScreen[None]):
    BINDINGS: ClassVar = [("escape", "close", "Zurück")]

    def __init__(
        self,
        initial_school_class_id: str | None = None,
        *,
        subject_id: str | None = None,
    ) -> None:
        super().__init__()
        self.initial_school_class_id = initial_school_class_id
        self.subject_id = subject_id
        self.school_classes: list[SchoolClass] = []
        self.school_classes_by_id: dict[str, SchoolClass] = {}
        self.subjects: list[Subject] = []
        self.sequences: list[Sequence] = []
        self._view_timer: Timer | None = None
        self._pending_target: tuple[str, str] | None = None
        # Nur für diesen geöffneten Screen: erneutes Öffnen liest aktuelle Dateien.
        self._progress_cache: dict[str, ClassProgress] = {}
        self._views: dict[tuple[str, str], TeachingLogView] = {}

    def compose(self) -> ComposeResult:
        with Horizontal(id="teaching-log-screen"):
            with Vertical(id="teaching-log-navigation"):
                picker = ViewPicker(id="teaching-log-class-picker")
                picker.border_title = "KLASSEN"
                yield picker

            content = Container(id="teaching-log-content")
            content.border_title = "Unterrichtsprotokoll"
            yield content

        yield PultFooter()

    async def on_mount(self) -> None:
        config = self.app_config
        try:
            self.school_classes = load_school_classes(
                config.root,
                config.active_school_year,
            )
            self.school_classes_by_id = {
                school_class.id: school_class for school_class in self.school_classes
            }
            self.subjects = load_subjects(config.root)
            self.sequences = self.sequence_library
        except (OSError, KeyError, ValueError) as error:
            self.notify(
                f"Die Protokollübersicht konnte nicht geladen werden: {error}",
                severity="error",
            )
            return

        picker = self.query_one("#teaching-log-class-picker", ViewPicker)
        # Die initiale Auswahl wird unten genau einmal ausdrücklich angezeigt.
        with self.prevent(OptionList.OptionHighlighted):
            picker.refresh_options(
                self.school_classes, self.subjects, include_home=False
            )
            picker.focus()

            if not self.school_classes:
                await self._show_empty_state("Es wurden noch keine Klassen angelegt.")
                return

            selected_id = (
                self.initial_school_class_id
                if self.initial_school_class_id in self.school_classes_by_id
                else self.school_classes[0].id
            )
            targets = list(picker.class_subjects_by_option_id.values())
            picker.highlighted = next(
                (
                    index
                    for index, (class_id, subject_id) in enumerate(targets)
                    if class_id == selected_id and subject_id == self.subject_id
                ),
                next(
                    index
                    for index, (class_id, _) in enumerate(targets)
                    if class_id == selected_id
                ),
            )
            self.subject_id = targets[picker.highlighted][1]
        await self.show_teaching_log(self.school_classes_by_id[selected_id])

    @on(OptionList.OptionHighlighted, "#teaching-log-class-picker")
    def school_class_highlighted(
        self,
        event: OptionList.OptionHighlighted,
    ) -> None:
        if event.option_id is None:
            return

        picker = self.query_one("#teaching-log-class-picker", ViewPicker)
        self._pending_target = picker.class_subjects_by_option_id[event.option_id]
        if self._view_timer is not None:
            self._view_timer.stop()
        self._view_timer = self.set_timer(0.08, self._show_pending_log)

    async def _show_pending_log(self) -> None:
        self._view_timer = None
        if self._pending_target is None or self.app.screen is not self:
            return
        school_class_id, self.subject_id = self._pending_target
        self._pending_target = None
        school_class = self.school_classes_by_id.get(school_class_id)
        if school_class is not None:
            await self.show_teaching_log(school_class)

    async def show_teaching_log(self, school_class: SchoolClass) -> None:
        config = self.app_config
        try:
            progress = self._progress_cache.get(school_class.id)
            if progress is None:
                progress = load_class_progress(
                    config.root, config.active_school_year, school_class.id
                )
                validate_class_progress(progress, school_class, self.sequences)
                self._progress_cache[school_class.id] = progress
        except (OSError, KeyError, StopIteration, ValueError) as error:
            self.notify(
                f"Das Protokoll für {school_class.id} konnte nicht geladen werden: {error}",
                severity="error",
            )
            return

        content = self.query_one("#teaching-log-content", Container)
        subject = next(s for s in self.subjects if s.id == self.subject_id)
        content.border_title = (
            f"Unterrichtsprotokoll · {school_class.id} · {subject.name}"
        )
        key = (school_class.id, subject.id)
        for view in self._views.values():
            view.display = False
        if key in self._views:
            self._views[key].display = True
            return
        view = TeachingLogView(
            school_class,
            tuple(
                entry
                for entry in progress.entries
                if self.subject_id is None or entry.subject_id == self.subject_id
            ),
            self.subjects,
            self.sequences,
            subject_id=self.subject_id,
        )
        self._views[key] = view
        await content.mount(view)

    async def _show_empty_state(self, message: str) -> None:
        content = self.query_one("#teaching-log-content", Container)
        await content.remove_children()
        await content.mount(Label(message, classes="teaching-log-empty"))

    def action_close(self) -> None:
        if self._view_timer is not None:
            self._view_timer.stop()
        self.dismiss()
