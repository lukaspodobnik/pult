from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class SetupScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "Willkommen! Schooltools muss zuerst eingerichtet werden."
        )
        yield Footer()
