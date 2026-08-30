


from textual.app import ComposeResult
from textual.widgets import Footer, Header

from schooltools_tui.screens.base import SchooltoolsScreen


class SchoolYearSetupScreen(SchooltoolsScreen[str | None]):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
