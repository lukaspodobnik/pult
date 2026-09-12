from rich.cells import cell_len
from textual.app import ComposeResult
from textual.widgets import Footer, Static
from textual.widgets._footer import FooterKey

SHORT_LABELS = {
    "open_next_lesson": "Öffnen",
    "add_extra_lesson": "Zusatzstunde",
    "change_active_sequence": "Sequenz",
    "toggle_material": "Ansicht",
    "edit_preparation": "Bearbeiten",
    "edit_metadata": "Stundendaten",
    "create_task": "Neu",
}
PRIORITY = {
    "go_home": 0,
    "close": 0,
    "back": 0,
    "cancel": 0,
    "open_next_lesson": 1,
    "create_task": 1,
    "edit_task": 1,
    "toggle_material": 1,
    "complete_next_lesson": 2,
    "edit_preparation": 2,
}


class PultFooter(Footer):
    """Zeige passende Aktionen; reserviere immer Platz für Hilfe und Beenden."""

    def __init__(self):
        super().__init__(compact=True)

    def on_resize(self) -> None:
        if self.is_mounted:
            self.call_after_refresh(self.recompose)

    def compose(self) -> ComposeResult:
        keys = [widget for widget in super().compose() if isinstance(widget, FooterKey)]
        reserved = []
        actions = []
        for key in keys:
            action = key.action.rsplit(".", 1)[-1]
            key.tooltip = key.description
            key.description = SHORT_LABELS.get(action, key.description)
            if action in {"show_binding_help", "quit"}:
                key.add_class(
                    "help-key" if action == "show_binding_help" else "quit-key"
                )
                reserved.append(key)
            else:
                actions.append(key)
        reserved.sort(key=lambda key: key.action.rsplit(".", 1)[-1] == "quit")
        actions.sort(key=lambda key: PRIORITY.get(key.action.rsplit(".", 1)[-1], 3))
        width = self.content_size.width or max(
            0, self.app.size.width - self.styles.padding.width
        )

        def required(key: FooterKey) -> int:
            return cell_len(key.key_display) + cell_len(key.description) + 2

        if sum(required(key) for key in reserved) > width:
            for key in reserved:
                key.description = ""
        available = width - sum(required(key) for key in reserved)
        for key in actions:
            needed = required(key)
            if needed <= available:
                yield key
                available -= needed
        yield Static(classes="footer-spacer")
        yield from reserved
