from textual.widgets import Static


class TerminalSizeNotice(Static):
    """Cover the current screen while the terminal is below the supported size."""

    DEFAULT_CSS = """
    TerminalSizeNotice {
        dock: top;
        layer: terminal-size;
        overlay: screen;
        width: 100%;
        height: 100%;
        background: $background;
        color: $foreground;
        content-align: center middle;
        padding: 1;
    }
    """
