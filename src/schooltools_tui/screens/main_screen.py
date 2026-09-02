from pathlib import Path
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Label, OptionList
from textual.widgets.option_list import Option

from schooltools_tui.period import load_periods
from schooltools_tui.school_class import SchoolClass, load_school_classes
from schooltools_tui.screens.base_screen import SchooltoolsScreen
from schooltools_tui.screens.edit_timetable_screen import (
    EditTimetableScreen,
    TimetableEditAction,
    TimetableEditResult,
)
from schooltools_tui.screens.setup_school_class_screen import SchoolClassSetupScreen
from schooltools_tui.subject import load_subjects
from schooltools_tui.timetable import (
    delete_timetable_entry,
    get_timetable_path,
    load_timetable,
    save_timetable_entry,
)
from schooltools_tui.views.home_view import HomeView
from schooltools_tui.views.school_class_view import SchoolClassView
from schooltools_tui.widgets.navigation import ManagementPicker, ViewPicker


class MainScreen(SchooltoolsScreen[None]):
    def __init__(self):
        super().__init__()
        self.school_classes_by_id: dict[str, SchoolClass] = {}

        config = self.app_config
        for school_class in load_school_classes(config.root, config.active_school_year):
            self.school_classes_by_id[school_class.id] = school_class

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
        config = self.app_config
        view_picker = self.query_one("#view-picker", ViewPicker)

        view_picker.refresh_options(
            load_school_classes(config.root, config.active_school_year)
        )

    def refresh_picker(self) -> None:
        config = self.app_config

        picker = self.query_one("#picker-options", OptionList)
        picker.clear_options()

        picker.add_option(Option("HOME", id="home"))
        for school_class in load_school_classes(config.root, config.active_school_year):
            option_id = f"class-{school_class.id}"
            picker.add_option(Option(school_class.id, id=option_id))
            self.school_classes_by_id[option_id] = school_class

        picker.highlighted = 0
        picker.focus()

    def school_class_registered(self, _: None) -> None:
        self.refresh_picker()

        # ---------------------------------------------------------------------------
        # |                         ViewPicker handling                             |
        # ---------------------------------------------------------------------------

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

        # ---------------------------------------------------------------------------
        # |                  ManagementPicker handling                              |
        # ---------------------------------------------------------------------------

    @on(OptionList.OptionSelected, "#management-picker")
    def management_picker_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option_id
        if option_id is None:
            return

        match option_id:
            case "edit-classes":
                pass
            case "sequence-library":
                pass
            case "edit-timetabel":
                pass

    @on(HomeView.EditTimetableSlot)
    def edit_timetable_slot(self, message: HomeView.EditTimetableSlot) -> None:
        config = self.app_config
        school_classes = load_school_classes(config.root, config.active_school_year)
        if not school_classes:
            self.notify(
                "Lege zuerst mindestens eine Klasse an.",
                severity="warning",
            )
            return

        subjects = load_subjects(config.root)
        self.app.push_screen(
            EditTimetableScreen(
                weekday=message.weekday,
                period=message.period,
                entry=message.entry,
                school_classes=school_classes,
                subjects=subjects,
            ),
            self.timetable_edited,
        )

    async def timetable_edited(self, result: TimetableEditResult | None) -> None:
        if result is None:
            return

        config = self.app_config
        path = get_timetable_path(config.root, config.active_school_year)

        if result.action is TimetableEditAction.SAVE:
            save_timetable_entry(path, result.entry)
        else:
            delete_timetable_entry(
                path,
                result.entry.weekday,
                result.entry.period,
            )

        await self.show_home_view()
