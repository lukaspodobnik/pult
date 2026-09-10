from textual.app import ComposeResult
from textual.widgets import Footer, Static
from textual.widgets._footer import FooterKey


class PultFooter(Footer):
    """Ordne lokale Befehle links und die globale Beenden-Aktion rechts."""

    def compose(self) -> ComposeResult:
        quit_key = None
        has_navigation = False
        widgets = list(super().compose())
        for widget in widgets:
            if (
                isinstance(widget, FooterKey)
                and widget.action.rsplit(".", 1)[-1] == "go_home"
            ):
                yield widget
                yield Static(classes="overview-spacer")
        for widget in widgets:
            if isinstance(widget, FooterKey):
                action = widget.action.rsplit(".", 1)[-1]
                if action == "go_home":
                    continue
                if action == "quit":
                    widget.add_class("quit-key")
                    quit_key = widget
                    continue
                elif action == "show_teaching_log":
                    widget.add_class("navigation-key")
                    has_navigation = True
                    yield Static(classes="footer-spacer navigation-spacer")
            yield widget
            if isinstance(widget, FooterKey) and widget.action.rsplit(".", 1)[-1] == "open_next_lesson":
                yield Static(classes="lesson-open-spacer")
        if quit_key is not None:
            if has_navigation:
                quit_key.add_class("balanced-quit")
                yield Static(classes="footer-spacer")
            yield quit_key
