from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Label, OptionList
from textual.widgets.option_list import Option

from schooltools_tui.initialization.school_year import (
    get_school_year_options,
    initialize_school_year,
)
from schooltools_tui.screens.base import SchooltoolsScreen


class SchoolYearSetupScreen(SchooltoolsScreen[str]):
    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id="school-year-setup-form"):
            yield Label("Schuljahr einrichten", id="school-year-setup-title")
            yield Label(
                "Wähle das Schuljahr, mit dem du arbeiten möchtest.",
                id="school-year-setup-description",
            )
            yield OptionList(
                *[
                    Option(label, id=f"year-{year}")
                    for label, year in get_school_year_options()
                ],
                id="school-years",
            )

        yield Footer()

    def on_mount(self) -> None:
        option_list = self.query_one("#school-years", OptionList)
        option_list.highlighted = 1
        option_list.focus()

    @on(OptionList.OptionSelected, "#school-years")
    def select_school_year(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option_id
        if option_id is None:
            return

        year = option_id.removeprefix("year-")

        initialize_school_year(self.app_config.root, year)

        self.dismiss(year)
