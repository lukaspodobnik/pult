"""Fullscreen teaching-view experiment; independent of Pult user data."""

import argparse
import math
import re
import tomllib

from PIL import Image as PILImage
from rendering import BASE, blocks, figure_image, formula_image, prepare_assets
from rich.cells import cell_len
from rich.text import Text
from textual.app import App
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Markdown, OptionList, Static
from textual.widgets.option_list import Option


def load_lessons():
    return tomllib.loads((BASE / "lessons.toml").read_text())["lessons"]


class Material(Vertical):
    def __init__(self, source, image_widget=None):
        super().__init__(classes="material")
        self.source, self.image_widget = source, image_widget

    def graphic(self, kind, value):
        path = formula_image(value) if kind == "math" else figure_image(value)
        widget = self.image_widget(
            path, classes="formula" if kind == "math" else "figure"
        )
        with PILImage.open(path) as image:
            # MathJax's ex is 16 source pixels. Keep one scale for all formulas.
            widget.styles.width = (
                max(2, math.ceil(image.width / 12))
                if kind == "math"
                else (60 if value == "parabel" else 38)
            )
        widget.styles.max_width = "100%"
        widget.styles.height = "auto"
        return widget

    def compose(self):
        for kind, value, caption in blocks(self.source):
            if kind == "text":
                yield Markdown(value)
            elif kind == "inline":
                yield InlineMath(value, self)
            elif self.image_widget is None:
                yield Static(
                    value if kind == "math" else f"Abbildung: {caption}",
                    classes="text-fallback",
                    markup=False,
                )
            else:
                yield self.graphic(kind, value)
                if caption:
                    yield Static(caption, classes="caption", markup=False)


class InlineMath(Vertical):
    """Wrap terminal text around atomic formula images, without rasterizing text."""

    def __init__(self, tokens, material):
        super().__init__(classes="inline-flow")
        self.tokens, self.material = tokens, material
        self._line_width = 0

    async def on_mount(self):
        self.call_after_refresh(self.build_lines)

    def on_resize(self):
        self.call_after_refresh(self.build_lines)

    async def build_lines(self):
        available = self.content_size.width
        if available <= 1 or available == self._line_width:
            return
        self._line_width = available
        rows, row, used = [], [], 0
        style = []
        for token in self.tokens:
            if token.type in {"strong_open", "em_open"}:
                style.append("bold" if token.type == "strong_open" else "italic")
                continue
            if token.type in {"strong_close", "em_close"}:
                if style:
                    style.pop()
                continue
            if token.type == "math_inline":
                widget = (
                    self.material.graphic("math", token.content)
                    if self.material.image_widget
                    else Static(token.content, classes="inline-text", markup=False)
                )
                width = (
                    int(widget.styles.width.value) + 2
                    if self.material.image_widget
                    else cell_len(token.content)
                )
                pieces = [(widget, width)]
            elif token.type in {"text", "code_inline", "softbreak", "hardbreak"}:
                text = token.content or " "
                pieces = [
                    (
                        Static(
                            Text(word, style=" ".join(style)), classes="inline-text"
                        ),
                        cell_len(word),
                    )
                    for word in re.findall(r"\s+|\S+", text)
                ]
            else:
                continue
            for widget, width in pieces:
                if row and used + width > available:
                    rows.append(Horizontal(*row, classes="inline-math"))
                    row, used = [], 0
                row.append(widget)
                used += width
        if row:
            rows.append(Horizontal(*row, classes="inline-math"))
        await self.remove_children()
        await self.mount(*rows)
        self.refresh(layout=True)
        self.screen.refresh(layout=True)


class MaterialPane(VerticalScroll):
    can_focus = True
    can_focus_children = False


class UnterrichtApp(App):
    TITLE = "Pult · Unterricht"
    CSS_PATH = "style.tcss"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("space", "toggle_material", "Vorbereitung / Aufgaben", priority=True),
        Binding("tab", "next_pane", "Bereich", priority=True),
        Binding("b", "example", "Nächste Stunde", show=False),
        Binding("j", "scroll_material(1)", show=False),
        Binding("k", "scroll_material(-1)", show=False),
        Binding("q", "quit", "Beenden"),
    ]

    def __init__(self, *, image_widget=None, graphics="Textmodus"):
        super().__init__()
        self.lessons = load_lessons()
        self.index = 0
        self.image_widget, self.graphics = image_widget, graphics
        self.show_tasks = False

    @property
    def lesson(self):
        return self.lessons[self.index]

    def material(self, file):
        return Material((BASE / "materials" / file).read_text(), self.image_widget)

    def task_materials(self):
        for number, task in enumerate(self.lesson["tasks"], 1):
            yield Static(
                f"{number} · {task['title']}", classes="task-title", markup=False
            )
            yield self.material(task["text"])
            yield Static("Lösung", classes="solution-title")
            yield self.material(task["solution"])

    def plan(self):
        content = Text()
        for number, (_, phase, action, material) in enumerate(self.lesson["phases"]):
            if number:
                content.append("\n\n")
            content.append(phase, style="bold #a9d6bf")
            content.append("\n\n" + action)
            if material:
                content.append("\n" + material, style="#94a9ad")
        return content

    def compose(self):
        with Horizontal(id="workspace"):
            with Vertical(id="navigation"):
                with Vertical(id="sequence-heading"):
                    yield Static("", id="sequence-context", markup=False)
                with Vertical(id="lesson-navigation"):
                    yield OptionList(id="lesson-list")
                    yield Static("↑ ↓ wählen · Enter öffnen", id="nav-hint")
            with Vertical(id="primary"):
                with MaterialPane(id="preparation"):
                    yield self.material(self.lesson["note"])
                with MaterialPane(id="tasks"):
                    yield from self.task_materials()
            with Vertical(id="orientation"):
                with MaterialPane(id="goals"):
                    yield Static(self.lesson["goal"], id="goal", markup=False)
                with MaterialPane(id="schedule"):
                    yield Static(self.plan(), id="plan")
        yield Footer()

    def on_mount(self):
        self.query_one("#sequence-heading").border_title = "SEQUENZ"
        self.query_one("#lesson-navigation").border_title = "STUNDEN"
        self.query_one("#goals").border_title = "ZIELE"
        self.query_one("#schedule").border_title = "VERLAUF"
        self.refresh_navigation()
        self.update_view()

    def refresh_navigation(self):
        context = self.lesson["context"]
        self.query_one("#sequence-context", Static).update(context.replace(" · ", "\n"))
        listing = self.query_one("#lesson-list", OptionList)
        indices = [
            i for i, lesson in enumerate(self.lessons) if lesson["context"] == context
        ]
        if getattr(self, "sequence_indices", None) == indices:
            listing.highlighted = indices.index(self.index)
            return
        listing.clear_options()
        self.sequence_indices = indices
        for number, index in enumerate(self.sequence_indices, 1):
            title = self.lessons[index]["title"]
            listing.add_option(Option(f"{number:02}  {title}", id=f"lesson-{index}"))
        listing.highlighted = self.sequence_indices.index(self.index)

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        await self.open_lesson(int(event.option.id.removeprefix("lesson-")))

    def update_view(self):
        self.query_one("#preparation").display = not self.show_tasks
        self.query_one("#tasks").display = self.show_tasks
        for selector, label in [
            ("#preparation", "Vorbereitung"),
            ("#tasks", "Aufgaben"),
        ]:
            pane = self.query_one(selector)
            pane.border_title = self.lesson["title"]
            pane.border_subtitle = label
        self.query_one("#tasks" if self.show_tasks else "#preparation").focus()
        self.call_after_refresh(self.refresh_inline_math)

    async def refresh_inline_math(self):
        for flow in self.query(InlineMath):
            if flow.display and flow.content_size.width > 1:
                await flow.build_lines()

    def action_toggle_material(self):
        self.show_tasks = not self.show_tasks
        self.update_view()

    def action_next_pane(self):
        panes = [
            "lesson-list",
            "tasks" if self.show_tasks else "preparation",
            "goals",
            "schedule",
        ]
        current = getattr(self.focused, "id", None)
        target = (
            panes[(panes.index(current) + 1) % len(panes)]
            if current in panes
            else panes[0]
        )
        self.query_one(f"#{target}").focus()

    def action_scroll_material(self, direction):
        if isinstance(self.focused, MaterialPane):
            self.focused.scroll_relative(y=direction * 3, animate=False)

    async def action_example(self):
        await self.open_lesson((self.index + 1) % len(self.lessons))

    async def open_lesson(self, index):
        self.index = index
        for selector, widgets in [
            ("#preparation", [self.material(self.lesson["note"])]),
            ("#tasks", list(self.task_materials())),
        ]:
            pane = self.query_one(selector)
            await pane.remove_children()
            await pane.mount(*widgets)
            pane.scroll_home(animate=False)
        for selector, value in [
            ("#goal", self.lesson["goal"]),
            ("#plan", self.plan()),
        ]:
            self.query_one(selector, Static).update(value)
        self.query_one("#schedule").scroll_home(animate=False)
        self.query_one("#goals").scroll_home(animate=False)
        self.refresh_navigation()
        self.show_tasks = False
        self.update_view()


def main():
    parser = argparse.ArgumentParser(description="Pults separate Unterrichtsansicht")
    parser.add_argument("--graphics", choices=["auto", "sixel", "off"], default="auto")
    args = parser.parse_args()
    image_widget = None
    label = "Textmodus (Formelquellen)"
    if args.graphics != "off":
        # Detection must happen before Textual takes over the terminal.
        from textual_image.widget import Image, SixelImage

        image_widget = SixelImage if args.graphics == "sixel" else Image
        label = "Sixel" if image_widget is SixelImage else "Automatische Grafik"
        if image_widget is SixelImage:
            from sixel import StableSixelImage

            image_widget = StableSixelImage
        print("Bereite Formeln und Abbildungen vor …", flush=True)
        prepare_assets(load_lessons())
    UnterrichtApp(image_widget=image_widget, graphics=label).run()


if __name__ == "__main__":
    main()
