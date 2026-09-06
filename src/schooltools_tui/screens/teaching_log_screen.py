from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Label, OptionList
from textual.widgets.option_list import Option

from schooltools_tui.curriculum.sequence import Sequence
from schooltools_tui.progress.class_progress import (
    load_class_progress,
    validate_class_progress,
)
from schooltools_tui.school.school_class import SchoolClass, load_school_classes
from schooltools_tui.school.subject import Subject, load_subjects
from schooltools_tui.screens.base_screen import SchooltoolsScreen
from schooltools_tui.views.teaching_log_view import TeachingLogView


class TeachingLogScreen(SchooltoolsScreen[None]):
    BINDINGS: ClassVar = [("escape", "close", "Zurück")]

    def __init__(self, initial_school_class_id: str | None = None) -> None:
        super().__init__()
        self.initial_school_class_id = initial_school_class_id
        self.school_classes: list[SchoolClass] = []
        self.school_classes_by_id: dict[str, SchoolClass] = {}
        self.subjects: list[Subject] = []
        self.sequences: list[Sequence] = []

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="teaching-log-screen"):
            with Vertical(id="teaching-log-navigation"):
                yield Label("KLASSEN", id="teaching-log-navigation-title")
                yield OptionList(id="teaching-log-class-picker")

            yield Container(id="teaching-log-content")

        yield Footer()

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
            self.notify(str(error), severity="error")
            return

        picker = self.query_one("#teaching-log-class-picker", OptionList)
        # Die initiale Auswahl wird unten genau einmal ausdrücklich angezeigt.
        with self.prevent(OptionList.OptionHighlighted):
            picker.add_options(
                Option(school_class.id, id=f"class-{school_class.id}")
                for school_class in self.school_classes
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
            picker.highlighted = next(
                index
                for index, school_class in enumerate(self.school_classes)
                if school_class.id == selected_id
            )
        await self.show_teaching_log(self.school_classes_by_id[selected_id])

    @on(OptionList.OptionHighlighted, "#teaching-log-class-picker")
    async def school_class_highlighted(
        self,
        event: OptionList.OptionHighlighted,
    ) -> None:
        if event.option_id is None:
            return

        school_class_id = event.option_id.removeprefix("class-")
        school_class = self.school_classes_by_id.get(school_class_id)
        if school_class is not None:
            await self.show_teaching_log(school_class)

    async def show_teaching_log(self, school_class: SchoolClass) -> None:
        config = self.app_config
        try:
            progress = load_class_progress(
                config.root,
                config.active_school_year,
                school_class.id,
            )
            validate_class_progress(progress, school_class, self.sequences)
        except (OSError, KeyError, StopIteration, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        content = self.query_one("#teaching-log-content", Container)
        await content.remove_children()
        await content.mount(
            TeachingLogView(
                school_class,
                progress.entries,
                self.subjects,
                self.sequences,
            )
        )

    async def _show_empty_state(self, message: str) -> None:
        content = self.query_one("#teaching-log-content", Container)
        await content.remove_children()
        await content.mount(Label(message, classes="teaching-log-empty"))

    def action_close(self) -> None:
        self.dismiss()
