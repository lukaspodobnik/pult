from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Footer, Header, Label, OptionList

from schooltools_tui.curriculum.sequence import Sequence, load_sequence_library
from schooltools_tui.progress.class_progress import (
    ClassProgress,
    load_class_progress,
    save_class_progress,
    validate_class_progress,
)
from schooltools_tui.progress.commands import (
    LessonCompletionState,
    ProgressCommandError,
    complete_lesson,
    set_active_sequence,
)
from schooltools_tui.progress.queries import (
    get_available_next_sequences,
    get_next_planned_lesson,
    get_next_planned_lesson_for_class,
    get_suggested_next_sequence,
)
from schooltools_tui.school.period import load_periods
from schooltools_tui.school.school_class import SchoolClass, load_school_classes
from schooltools_tui.school.school_year import get_school_year_start
from schooltools_tui.school.subject import load_subjects
from schooltools_tui.school.timetable import get_timetable_path, load_timetable
from schooltools_tui.screens.base_screen import SchooltoolsScreen
from schooltools_tui.screens.edit_classes_screen import EditClassesScreen
from schooltools_tui.screens.edit_timetable_screen import EditTimetableScreen
from schooltools_tui.screens.select_next_sequence_screen import (
    SelectNextSequenceScreen,
)
from schooltools_tui.screens.sequence_library_screen import SequenceLibraryScreen
from schooltools_tui.views.home_view import HomeView
from schooltools_tui.views.school_class_view import SchoolClassView
from schooltools_tui.widgets.navigation import ManagementPicker, ViewPicker


class MainScreen(SchooltoolsScreen[None]):
    BINDINGS: ClassVar = [
        ("n", "complete_next_lesson", "Stunde abschließen"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.school_classes_by_id: dict[str, SchoolClass] = {}
        self.active_school_class_id: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main"):
            with Vertical(id="navigation"):
                yield Label("ANSICHTEN", id="view-label")
                yield ViewPicker(id="view-picker")

                yield Label("VERWALTUNG", id="management-label")
                yield ManagementPicker(id="management-picker")

            with Container(id="content"):
                pass

        yield Footer()

    def on_mount(self) -> None:
        self.refresh_view_picker()
        self.query_one("#view-picker", ViewPicker).focus()

    def refresh_view_picker(self) -> None:
        view_picker = self.query_one("#view-picker", ViewPicker)
        highlighted_option_id = None
        if view_picker.highlighted is not None:
            option = view_picker.get_option_at_index(view_picker.highlighted)
            if option.id is not None:
                highlighted_option_id = str(option.id)

        self.refresh_school_classes()
        view_picker.refresh_options(
            list(self.school_classes_by_id.values()),
            highlighted_option_id,
        )

    def refresh_school_classes(self) -> None:
        config = self.app_config
        school_classes = load_school_classes(config.root, config.active_school_year)
        self.school_classes_by_id = {
            school_class.id: school_class for school_class in school_classes
        }

    @on(OptionList.OptionHighlighted, "#view-picker")
    async def view_picker_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        option_id = event.option_id
        if option_id is None:
            return

        if option_id == "home":
            await self.show_home_view()
            return

        await self.show_school_class_view(
            self.school_classes_by_id[option_id.removeprefix("class-")]
        )

    async def switch_view(self, view: Widget) -> None:
        content = self.query_one("#content", Container)

        await content.remove_children()
        await content.mount(view)

    async def show_home_view(self) -> None:
        self.active_school_class_id = None
        config = self.app_config
        path = get_timetable_path(config.root, config.active_school_year)
        timetable_entries = load_timetable(path)
        periods = load_periods(config.root)
        subjects = load_subjects(config.root)
        await self.switch_view(HomeView(timetable_entries, subjects, periods))

    async def show_school_class_view(self, school_class: SchoolClass) -> None:
        self.active_school_class_id = school_class.id
        await self.switch_view(SchoolClassView(school_class))

    async def refresh_current_view(self) -> None:
        if self.active_school_class_id is None:
            await self.show_home_view()
            return

        await self.show_school_class_view(
            self.school_classes_by_id[self.active_school_class_id]
        )

    async def save_progress_and_refresh(
        self,
        school_class: SchoolClass,
        progress: ClassProgress,
        sequences: list[Sequence],
    ) -> None:
        config = self.app_config
        validate_class_progress(progress, school_class, sequences)
        save_class_progress(
            config.root,
            config.active_school_year,
            school_class.id,
            progress,
        )
        await self.refresh_current_view()

    async def action_complete_next_lesson(self) -> None:
        config = self.app_config
        year = config.active_school_year

        try:
            school_classes = load_school_classes(config.root, year)
            self.school_classes_by_id = {
                school_class.id: school_class for school_class in school_classes
            }
            sequences = load_sequence_library(config.root)
            timetable_entries = load_timetable(
                get_timetable_path(config.root, year)
            )
            school_year_start = get_school_year_start(year)
            progress: ClassProgress | None = None

            if self.active_school_class_id is None:
                progresses_by_class_id = {
                    school_class.id: load_class_progress(
                        config.root,
                        year,
                        school_class.id,
                    )
                    for school_class in school_classes
                }
                planned_lesson = get_next_planned_lesson(
                    progresses_by_class_id,
                    sequences,
                    timetable_entries,
                    school_classes,
                    school_year_start,
                )
                if planned_lesson is not None:
                    progress = progresses_by_class_id[
                        planned_lesson.school_class_id
                    ]
            else:
                school_class = self.school_classes_by_id[
                    self.active_school_class_id
                ]
                progress = load_class_progress(
                    config.root,
                    year,
                    school_class.id,
                )
                planned_lesson = get_next_planned_lesson_for_class(
                    progress,
                    sequences,
                    timetable_entries,
                    school_class,
                    school_year_start,
                )

            if planned_lesson is None:
                self.notify(
                    "Es gibt keine offene geplante Stunde.",
                    severity="warning",
                )
                return

            assert progress is not None
            school_class = self.school_classes_by_id[
                planned_lesson.school_class_id
            ]
            result = complete_lesson(
                progress,
                planned_lesson,
                sequences,
            )
        except (OSError, KeyError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        if result.state is LessonCompletionState.NEEDS_NEXT_SEQUENCE:
            available_sequences = get_available_next_sequences(
                result.progress,
                sequences,
                result.subject_id,
                school_class.grade_level,
            )
            suggested_sequence = get_suggested_next_sequence(
                result.progress,
                sequences,
                result.subject_id,
                school_class.grade_level,
            )
            assert suggested_sequence is not None

            async def next_sequence_selected(sequence_id: str | None) -> None:
                if sequence_id is None:
                    return

                try:
                    updated_progress = set_active_sequence(
                        result.progress,
                        result.subject_id,
                        sequence_id,
                        school_class.grade_level,
                        sequences,
                    )
                    await self.save_progress_and_refresh(
                        school_class,
                        updated_progress,
                        sequences,
                    )
                except (OSError, ProgressCommandError, ValueError) as error:
                    self.notify(str(error), severity="error")
                    return

                self.notify(
                    f"{school_class.id}: '{planned_lesson.lesson.title}' "
                    "abgeschlossen und nächste Sequenz aktiviert."
                )

            self.app.push_screen(
                SelectNextSequenceScreen(
                    available_sequences,
                    suggested_sequence.id,
                ),
                next_sequence_selected,
            )
            return

        try:
            await self.save_progress_and_refresh(
                school_class,
                result.progress,
                sequences,
            )
        except (OSError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        if result.state is LessonCompletionState.COMPLETES_SUBJECT:
            self.notify(
                f"{school_class.id}: '{planned_lesson.lesson.title}' abgeschlossen; "
                "das Fach ist vollständig abgeschlossen."
            )
        else:
            self.notify(
                f"{school_class.id}: '{planned_lesson.lesson.title}' abgeschlossen."
            )

    @on(OptionList.OptionSelected, "#management-picker")
    def management_picker_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option_id
        if option_id is None:
            return

        match option_id:
            case "edit-classes":
                self.app.push_screen(EditClassesScreen(), self.classes_edited)
            case "sequence-library":
                self.app.push_screen(SequenceLibraryScreen())
            case "edit-timetable":
                self.app.push_screen(
                    EditTimetableScreen(), self.timetable_edit_finished
                )

    def classes_edited(self, _: None) -> None:
        self.refresh_view_picker()

    async def timetable_edit_finished(self, _: None) -> None:
        if self.query(HomeView):
            await self.show_home_view()
