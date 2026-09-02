from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Footer, Header, Label, OptionList

from schooltools_tui.period import load_periods
from schooltools_tui.school_class import SchoolClass, load_school_classes
from schooltools_tui.screens.base_screen import SchooltoolsScreen
from schooltools_tui.screens.edit_timetable_screen import EditTimetableScreen
from schooltools_tui.screens.edit_classes_screen import EditClassesScreen
from schooltools_tui.subject import load_subjects
from schooltools_tui.timetable import get_timetable_path, load_timetable
from schooltools_tui.views.home_view import HomeView
from schooltools_tui.views.school_class_view import SchoolClassView
from schooltools_tui.widgets.navigation import ManagementPicker, ViewPicker


class MainScreen(SchooltoolsScreen[None]):
    def __init__(self) -> None:
        super().__init__()
        self.school_classes_by_id: dict[str, SchoolClass] = {}

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
        config = self.app_config
        path = get_timetable_path(config.root, config.active_school_year)
        timetable_entries = load_timetable(path)
        periods = load_periods(config.root)
        subjects = load_subjects(config.root)
        await self.switch_view(HomeView(timetable_entries, subjects, periods))

    async def show_school_class_view(self, school_class: SchoolClass) -> None:
        await self.switch_view(SchoolClassView(school_class))

    @on(OptionList.OptionSelected, "#management-picker")
    def management_picker_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option_id
        if option_id is None:
            return

        match option_id:
            case "edit-classes":
                self.app.push_screen(EditClassesScreen(), self.classes_edited)
            case "sequence-library":
                pass
            case "edit-timetable":
                self.app.push_screen(
                    EditTimetableScreen(), self.timetable_edit_finished
                )

    def classes_edited(self, _: None) -> None:
        self.refresh_view_picker()

    async def timetable_edit_finished(self, _: None) -> None:
        if self.query(HomeView):
            await self.show_home_view()
