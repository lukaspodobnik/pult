from rich.text import Text
from textual.widgets import Static


class CappedText(Static):
    """Kürze nur die Darstellung passend zur Breite auf höchstens einige Zeilen."""

    def __init__(
        self, text: str = "", *, lines: int = 1, classes: str | None = None
    ) -> None:
        super().__init__(text, classes=classes, markup=False)
        self.max_lines = lines

    def render(self) -> Text:
        width = max(1, self.content_size.width)
        text = Text(" ".join(str(self.content).split()))
        if self.max_lines == 1:
            text.truncate(width, overflow="ellipsis")
            return text
        lines = text.wrap(self.app.console, width)
        if len(lines) > self.max_lines:
            lines = lines[: self.max_lines]
            lines[-1].truncate(max(0, width - 1))
            lines[-1].append("…")
        return Text("\n").join(lines)

    def on_resize(self) -> None:
        self.refresh()
