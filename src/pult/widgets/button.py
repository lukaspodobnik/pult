"""Gemeinsamer Button-Typ; Fokus und Hover werden über den Rahmen dargestellt."""

from textual.widgets import Button as TextualButton


class Button(TextualButton):
    """Appweite Darstellung aus styles/app.tcss."""
