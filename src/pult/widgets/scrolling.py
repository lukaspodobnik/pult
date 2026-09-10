"""Einheitliche Scrollleisten ohne Änderungen an den Inhaltsabständen."""

from typing import Generic, TypeVar, cast

from textual.containers import Horizontal as TextualHorizontal
from textual.containers import Vertical as TextualVertical
from textual.containers import VerticalScroll as TextualVerticalScroll
from textual.widget import Widget
from textual.widgets import DataTable as TextualDataTable
from textual.widgets import OptionList as TextualOptionList
from textual.widgets import Tree as TextualTree


class EdgeScrollbars:
    def _arrange_scrollbars(self, region):
        # Textual platziert Scrollleisten innerhalb des Paddings. Nur die Leisten
        # bis an dessen Außenkante verschieben; Rahmen und Inhalt bleiben stehen.
        widget = cast(Widget, self)
        for scrollbar, area in super()._arrange_scrollbars(region):  # pyright: ignore[reportAttributeAccessIssue]
            if scrollbar is widget.vertical_scrollbar:
                area = area.translate((widget.styles.padding.right, 0))
            elif scrollbar is widget.horizontal_scrollbar:
                area = area.translate((0, widget.styles.padding.bottom))
            else:
                area = area.translate(
                    (widget.styles.padding.right, widget.styles.padding.bottom)
                )
            yield scrollbar, area


class VerticalScroll(EdgeScrollbars, TextualVerticalScroll):
    pass


class Vertical(EdgeScrollbars, TextualVertical):
    pass


class Horizontal(EdgeScrollbars, TextualHorizontal):
    pass


class OptionList(EdgeScrollbars, TextualOptionList):
    pass


class DataTable(EdgeScrollbars, TextualDataTable):
    pass


TreeData = TypeVar("TreeData")


class Tree(EdgeScrollbars, TextualTree[TreeData], Generic[TreeData]):
    pass
