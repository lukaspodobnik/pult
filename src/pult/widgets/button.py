"""Buttons mit Hervorhebung ausschließlich innerhalb des Rahmens."""

from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.widgets import Button as TextualButton


class Button(TextualButton):
    COMPONENT_CLASSES = {"button--focus", "button--hover"}
    DEFAULT_CSS = """
    Button > .button--focus {
        background: $primary;
        color: auto 100%;
        text-style: bold;
    }
    Button > .button--hover {
        background: $foreground 20%;
        color: $foreground;
    }
    """

    def render_line(self, y: int) -> Strip:
        line = super().render_line(y)
        if self.disabled:
            return line
        if self.has_focus or self.has_class("-active"):
            highlight = self.get_component_rich_style("button--focus")
        elif self.mouse_hover:
            highlight = self.get_component_rich_style("button--hover")
        else:
            return line
        return Strip(
            Segment(text, (style or Style()) + highlight, control)
            for text, style, control in line
        )
