from textual.app import ComposeResult
from textual.widgets import Footer, Static
from textual.widgets._footer import FooterKey


class SchooltoolsFooter(Footer):
    """Ordne lokale Befehle links und die globale Beenden-Aktion rechts."""

    def compose(self) -> ComposeResult:
        quit_key = None
        has_navigation = False
        for widget in super().compose():
            if isinstance(widget, FooterKey):
                action = widget.action.rsplit(".", 1)[-1]
                if action == "quit":
                    widget.add_class("quit-key")
                    quit_key = widget
                    continue
                elif action == "show_teaching_log":
                    widget.add_class("navigation-key")
                    has_navigation = True
                    yield Static(classes="footer-spacer navigation-spacer")
            yield widget
        if quit_key is not None:
            if has_navigation:
                quit_key.add_class("balanced-quit")
                yield Static(classes="footer-spacer")
            yield quit_key
