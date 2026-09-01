from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, OptionList
from textual.widgets.option_list import Option

from schooltools_tui.school_class import SchoolClass, load_school_classes
from schooltools_tui.screens.base_screen import SchooltoolsScreen
from schooltools_tui.screens.setup_school_class_screen import SchoolClassSetupScreen
from schooltools_tui.timetable import get_timetable_path, load_timetable
from schooltools_tui.views.home_view import HomeView
from schooltools_tui.views.school_class_view import SchoolClassView


class MainScreen(SchooltoolsScreen[None]):
    def __init__(self):
        super().__init__()
        self.school_classes_by_id: dict[str, SchoolClass] = {}

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main"):
            with Vertical(id="picker"):
                yield OptionList(id="picker-options")
                yield Button("Klasse anlegen", variant="primary", id="register-class")

            with Container(id="content"):
                pass

        yield Footer()

    def on_mount(self) -> None:
        self.refresh_picker()

    def refresh_picker(self) -> None:
        config = self.app_config
        school_classes = load_school_classes(config.root, config.active_school_year)

        picker = self.query_one("#picker-options", OptionList)
        picker.clear_options()

        picker.add_option(Option("HOME", id="home"))
        for school_class in school_classes:
            option_id = f"class-{school_class.id}"
            picker.add_option(Option(school_class.id, id=option_id))
            self.school_classes_by_id[option_id] = school_class

        picker.highlighted = 0
        picker.focus()


    @on(Button.Pressed, "#register-class")
    def register_class(self) -> None:
        self.app.push_screen(SchoolClassSetupScreen(), self.school_class_registered)

    def school_class_registered(self, _: None) -> None:
        self.refresh_picker()

    @on(OptionList.OptionHighlighted, "#picker-options")
    async def option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        option_id = event.option_id
        if option_id is None:
            return

        if option_id == "home":
            await self.show_home_view()
            return

        await self.show_school_class_view(self.school_classes_by_id[option_id])

    async def switch_view(self, view: Widget) -> None:
        content = self.query_one("#content", Container)

        await content.remove_children()
        await content.mount(view)

    async def show_home_view(self) -> None:
        config = self.app_config
        path = get_timetable_path(config.root, config.active_school_year)
        timetable_entries = load_timetable(path)
        await self.switch_view(HomeView(timetable_entries))

    async def show_school_class_view(self, school_class: SchoolClass) -> None:
        await self.switch_view(SchoolClassView(school_class))
