from textual.containers import Vertical, VerticalScroll


class FormFields(VerticalScroll):
    can_focus = False


class FormDialog(Vertical):
    """Gemeinsamer Rahmen für Formularinhalt und eine feste Aktionsleiste."""

    def __init__(self, title: str, *, id: str, wide: bool = False) -> None:
        super().__init__(id=id, classes="form-dialog wide" if wide else "form-dialog")
        self.border_title = title

    def on_mount(self) -> None:
        fields = self.query("Input, Select, SelectionList")
        if fields:
            fields.first().focus()
