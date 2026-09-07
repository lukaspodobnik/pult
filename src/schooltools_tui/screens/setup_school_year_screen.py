from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Header, Label, OptionList
from textual.widgets.option_list import Option

from schooltools_tui.initialization.school_year import initialize_school_year
from schooltools_tui.school.school_year import (
    get_likely_school_year,
    get_school_year_options,
)
from schooltools_tui.screens.base_screen import SchooltoolsScreen
from schooltools_tui.widgets.footer import SchooltoolsFooter


class SchoolYearSetupScreen(SchooltoolsScreen[str]):
    def compose(self) -> ComposeResult:
        school_year_options = get_school_year_options(self.app_config.root)

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
                    for label, year in school_year_options
                ],
                id="school-years",
            )

        yield SchooltoolsFooter()

    def on_mount(self) -> None:
        option_list = self.query_one("#school-years", OptionList)
        school_year_options = get_school_year_options(self.app_config.root)
        selected_school_year = get_likely_school_year(school_year_options)
        option_list.highlighted = [year for _, year in school_year_options].index(
            selected_school_year
        )
        option_list.focus()

    @on(OptionList.OptionSelected, "#school-years")
    def select_school_year(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option_id
        if option_id is None:
            return

        year = option_id.removeprefix("year-")

        try:
            initialize_school_year(self.app_config.root, year)
        except (OSError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        self.dismiss(year)
