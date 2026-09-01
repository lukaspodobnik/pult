from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, OptionList
from textual.widgets.option_list import Option

from schooltools_tui.school_class import load_school_classes
from schooltools_tui.screens.base_screen import SchooltoolsScreen
from schooltools_tui.screens.setup_school_class_screen import SchoolClassSetupScreen
from schooltools_tui.timetable import get_timetable_path, load_timetable
from schooltools_tui.views.home_view import HomeView


class MainScreen(SchooltoolsScreen[None]):
    def compose(self) -> ComposeResult:
        config = self.app_config
        timetable_entries = load_timetable(get_timetable_path(config.root, config.active_school_year))

        yield Header()

        with Horizontal(id="main"):
            with Vertical(id="picker"):
                yield OptionList(id="picker-options")
                yield Button("Klasse anlegen", variant="primary", id="register-class")

            with Container(id="content"):
                yield HomeView(timetable_entries)

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
            picker.add_option(Option(school_class.id, id=f"class-{school_class.id}"))

        picker.highlighted = 0
        picker.focus()


    @on(Button.Pressed, "#register-class")
    def register_class(self) -> None:
        self.app.push_screen(SchoolClassSetupScreen(), self.school_class_registered)

    def school_class_registered(self, _result: None) -> None:
        self.refresh_picker()
