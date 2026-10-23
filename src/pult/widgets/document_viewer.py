"""Dokumente in lesbarer Originalgröße, mit gemeinsamem Browser und Cache."""

import io
import math
from pathlib import Path

from PIL import Image as PILImage
from rich import box
from rich.markdown import Markdown as RichMarkdown
from rich.segment import Segment
from rich.style import Style
from rich.table import Table
from rich.text import Text
from textual import work
from textual.color import Color
from textual.geometry import Region
from textual.message import Message
from textual.strip import Strip
from textual.widgets import Markdown, Static

from pult.curriculum.material import Lesson
from pult.services.documents import material_rendering as graphics
from pult.services.documents.document_callouts import (
    resolve_callout_colors,
    text_document_parser,
)
from pult.services.documents.document_corners import round_document_tile
from pult.services.documents.document_rendering import (
    SEPARATOR_Y,
    DocumentRenderer,
    split_phase_time,
)
from pult.widgets.scrolling import Vertical, VerticalScroll


class DocumentPane(VerticalScroll):
    can_focus = True
    can_focus_children = False
    DEFAULT_CSS = """
    DocumentPane {height:1fr; padding:0; background:$surface; border:round $primary; overflow-x:hidden;}
    DocumentPane:focus {border:round $primary-lighten-2;}
    """

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        if self.is_mounted and round(old_value) != round(new_value):
            self.call_after_refresh(self.refresh_corners)

    def refresh_corners(self) -> None:
        for viewer in self.query(DocumentViewer):
            viewer.refresh_corners()

    def render_lines(self, crop: Region) -> list[Strip]:
        lines = super().render_lines(crop)
        # Round borders are terminal glyphs. Keep their entire cells on the
        # surrounding surface, while the interior retains the document color.
        border_style = Style(bgcolor=self.background_colors[0].rich_color)

        def frame_background(strip: Strip) -> Strip:
            return Strip(
                Segment.apply_style(strip, post_style=border_style), strip.cell_length
            )

        for index, line in enumerate(lines):
            y = crop.y + index
            if y in (0, self.outer_size.height - 1):
                lines[index] = frame_background(line)
            else:
                left = 1 if crop.x == 0 else 0
                right = line.cell_length - (
                    1 if crop.right == self.outer_size.width else 0
                )
                lines[index] = Strip.join(
                    [
                        frame_background(line.crop(0, left)),
                        line.crop(left, right),
                        frame_background(line.crop(right)),
                    ]
                )
        return lines


class DocumentViewer(Vertical):
    class Rendering(Message):
        def __init__(self, viewer: "DocumentViewer"):
            super().__init__()
            self.viewer = viewer

    class Ready(Message):
        def __init__(self, viewer: "DocumentViewer"):
            super().__init__()
            self.viewer = viewer

    DEFAULT_CSS = """
    DocumentViewer {height:auto; background:transparent; overflow:hidden hidden;}
    DocumentViewer .document-tile {width:100%; margin:0; padding:0;}
    DocumentViewer .document-tile > Widget {width:100%;height:100%;}
    DocumentViewer Markdown {height:auto;background:transparent;padding:0;margin:0;}
    DocumentViewer .document-status {height:auto;color:$text-muted;}
    """

    def __init__(
        self,
        source: str,
        path: Path,
        directory: Path,
        *,
        planning: Lesson | None = None,
        start_at_separator: bool = False,
    ):
        super().__init__(classes="document-viewer")
        self.source, self.path, self.directory = source, path, directory
        self.planning = planning
        self.start_at_separator = start_at_separator and planning is None
        self._initial_scroll_pending = self.start_at_separator
        self._separator_row: int | None = None
        self.renderer: DocumentRenderer | None = None
        self.signature = None
        self.rendered_signature = None
        self._cache_path: Path | None = None
        self.render_timer = None
        self.text_mode = False
        self.image_tiles = []
        self.corner_signatures = {}

    def compose(self):
        yield Vertical(
            Static("Dokument wird gesetzt …", classes="document-status"),
            id="document-body",
        )

    def on_mount(self):
        self.query_one("#document-body").styles.height = "auto"
        self.set_interval(0.5, self.schedule_render)
        self.call_after_refresh(self.schedule_render)

    def on_resize(self):
        self.schedule_render()

    def set_active(self, active: bool, *, reset_position: bool = False):
        self.display = active
        if not active:
            if self.render_timer:
                self.render_timer.stop()
            for worker in self.workers:
                if worker.node is self and not worker.is_cancelled:
                    worker.cancel()
            if self.rendered_signature != self.signature:
                self.signature = None
            return
        if reset_position:
            self._initial_scroll_pending = self.start_at_separator
        self.call_after_refresh(self.activate_document)

    def activate_document(self):
        self.schedule_render()
        self.position_continuation()
        if self.signature is not None and self.rendered_signature == self.signature:
            if self._cache_path is not None:
                DocumentRenderer.touch_cache(self._cache_path)
            self.post_message(self.Ready(self))

    def schedule_render(self):
        if not self.is_mounted or not self.display or self.content_size.width < 5:
            return
        pane = next((a for a in self.ancestors if isinstance(a, DocumentPane)), None)
        if pane is not None and not pane.display:
            return
        viewport_height = pane.scrollable_content_region.height if pane else 0
        variables = self.app.get_css_variables()
        # A subtle reading surface, lighter in dark themes and darker in light ones.
        background = (
            Color.parse(variables["surface"])
            .blend(Color.parse(variables["foreground"]), 0.05)
            .hex
        )
        colors = (background, variables["foreground"], variables["primary"])
        callout_colors = resolve_callout_colors(background, variables)
        config = getattr(self.app, "app_config", None)
        font = getattr(config, "document_font", "auto")
        signature = (
            self.content_size.width,
            colors,
            self.text_mode,
            font,
            viewport_height,
            getattr(getattr(self.app, "document_renderer", None), "generation", 0),
            callout_colors,
        )
        if signature == self.signature:
            self.refresh_corners()
            return
        first_render = self.signature is None
        self.signature = signature
        self.post_message(self.Rendering(self))
        self.styles.background = background
        self.query_one("#document-body").styles.background = background
        for ancestor in self.ancestors:
            if isinstance(ancestor, DocumentPane):
                ancestor.styles.background = background
                break
        if self.render_timer:
            self.render_timer.stop()
        if first_render:
            self.render_document(signature)
        else:
            # Resize/theme bursts still settle before repeating expensive layout.
            self.render_timer = self.set_timer(
                0.2, lambda: self.render_document(signature)
            )

    async def render_image(
        self, source: str, path: Path, planning: Lesson | None, signature
    ):
        width, colors, _text_mode, font, _height, _generation, callout_colors = (
            signature
        )
        if self.renderer is None:
            renderer = getattr(self.app, "document_renderer", None)
            if renderer is None:
                renderer = DocumentRenderer()
                setattr(self.app, "document_renderer", renderer)
            self.renderer = renderer
        assert self.renderer is not None
        cell_width, cell_height = graphics.CELL
        return await self.renderer.render(
            source,
            path,
            self.directory,
            width * cell_width,
            max(15, cell_height * 0.85),
            *colors,
            planning=planning,
            font=font,
            callout_colors=callout_colors,
        )

    async def prefetch(self, source: str, path: Path, planning: Lesson | None):
        if self.signature is not None and self.image_tiles:
            await self.render_image(source, path, planning, self.signature)

    @work(exclusive=True)
    async def render_document(self, signature):
        width, colors, text_mode, font, viewport_height, _generation, callout_colors = (
            signature
        )
        body = self.query_one("#document-body", Vertical)
        tiles = []
        separator_row = None
        cache_path = None
        try:
            if graphics.image_widget() is None or text_mode:
                widgets = self.fallback_widgets()
            else:
                cell_width, cell_height = graphics.CELL
                pixel_width = width * cell_width
                rendered_image = await self.render_image(
                    self.source, self.path, self.planning, signature
                )
                if not self.is_mounted or signature != self.signature:
                    return
                cache_path = (
                    rendered_image if isinstance(rendered_image, Path) else None
                )
                image_source = (
                    io.BytesIO(rendered_image)
                    if isinstance(rendered_image, bytes)
                    else rendered_image
                )
                with PILImage.open(image_source) as image:
                    if self.start_at_separator and SEPARATOR_Y in image.info:
                        y = float(image.info[SEPARATOR_Y])
                        if 0 <= y < image.height:
                            separator_row = math.floor(y / cell_height)
                    image = image.convert("RGB")
                    # Fill short documents to the viewport, including its lower corners.
                    minimum_height = viewport_height * cell_height
                    if image.height < minimum_height:
                        canvas = PILImage.new(
                            "RGB",
                            (pixel_width, minimum_height),
                            colors[0],
                        )
                        canvas.paste(image)
                        image = canvas
                    # Align tile boundaries to terminal rows; never shrink the whole document.
                    tile_height = cell_height * 40
                    widgets = []
                    for top in range(0, image.height, tile_height):
                        tile = image.crop(
                            (0, top, image.width, min(top + tile_height, image.height))
                        )
                        rows = math.ceil(tile.height / cell_height)
                        padded = PILImage.new(
                            "RGB", (pixel_width, rows * cell_height), colors[0]
                        )
                        padded.paste(tile)
                        factory = graphics.image_widget()
                        assert factory is not None
                        kwargs = (
                            {"paper_color": colors[0]}
                            if factory.__name__ == "StableSixelImage"
                            else {}
                        )
                        widget = factory(padded, classes="document-tile", **kwargs)
                        widget.styles.height = rows
                        widgets.append(widget)
                        tiles.append((widget, padded))
            if not self.is_mounted or signature != self.signature:
                return
            self.image_tiles = []
            self.corner_signatures.clear()
            # Keep the scroll range while replacement Markdown builds its blocks.
            body.styles.min_height = body.size.height
            await body.remove_children()
            await body.mount(*widgets)
            self.image_tiles = tiles
            self._separator_row = separator_row
            if tiles:
                body.styles.min_height = 0
            self.call_after_refresh(self.position_continuation)
            self.call_after_refresh(self.refresh_corners)
            self.rendered_signature = signature
            self._cache_path = cache_path
            self.post_message(self.Ready(self))
        except Exception as error:
            if self.is_mounted and signature == self.signature:
                self.image_tiles = []
                self.corner_signatures.clear()
                body.styles.min_height = body.size.height
                await body.remove_children()
                status = Static(
                    f"Textansicht · {error}"
                    if isinstance(error, ValueError)
                    else "Textansicht · Grafikdarstellung nicht verfügbar. Einstellungen → Dokumentdarstellung öffnen.",
                    markup=False,
                    classes="document-status",
                )
                status.tooltip = str(error)
                await body.mount(status, *self.fallback_widgets())
                self._separator_row = None
                self.call_after_refresh(self.position_continuation)
                self.rendered_signature = signature
                self._cache_path = None
                self.post_message(self.Ready(self))

    def on_markdown_table_of_contents_updated(
        self, event: Markdown.TableOfContentsUpdated
    ):
        # Markdown builds its blocks asynchronously, after the widget is mounted.
        self.query_one("#document-body").styles.min_height = 0
        self.call_after_refresh(self.position_continuation)

    def position_continuation(self) -> None:
        if not self.is_mounted or not self.display or not self.start_at_separator:
            return
        pane = next((a for a in self.ancestors if isinstance(a, DocumentPane)), None)
        if (
            pane is None
            or not pane.display
            or not self.region.width
            or not pane.scrollable_content_region.height
        ):
            return
        row = self._separator_row
        if not self.image_tiles:
            # Nested rules and literal examples in code do not mark a continuation.
            rule = next(iter(self.query("MarkdownHorizontalRule.level-0")), None)
            if rule is None:
                return
            body = self.query_one("#document-body", Vertical)
            row = max(0, rule.region.y - body.region.y)
        if row is not None and self._initial_scroll_pending:
            self._initial_scroll_pending = False
            if pane.max_scroll_y > 0:
                offset = (
                    self.region.y - pane.scrollable_content_region.y + pane.scroll_y
                )
                middle = pane.scrollable_content_region.height // 2
                # Use only the document's natural scroll range; no empty tail.
                target = min(pane.max_scroll_y, max(0, offset + row - middle))
                pane.scroll_to(y=target, animate=False, immediate=True)

    def refresh_corners(self) -> None:
        if not self.is_mounted or not self.display or not self.image_tiles:
            return
        pane = next((a for a in self.ancestors if isinstance(a, DocumentPane)), None)
        if pane is None or not pane.display:
            return
        viewport = pane.scrollable_content_region
        cell_width, cell_height = graphics.CELL
        radius = max(2, min(cell_width, cell_height))
        outside = pane.background_colors[0].hex
        for widget, original in self.image_tiles:
            if not widget.is_mounted:
                continue
            rectangle = (
                (viewport.x - widget.region.x) * cell_width,
                (viewport.y - widget.region.y) * cell_height,
                (viewport.right - widget.region.x) * cell_width,
                (viewport.bottom - widget.region.y) * cell_height,
            )
            # Only the tiles touching the visible corners need new image data.
            top, bottom = rectangle[1], rectangle[3]
            touches_corner = (
                -radius < top < original.height or 0 < bottom < original.height + radius
            )
            signature = (rectangle, outside) if touches_corner else None
            if (
                widget in self.corner_signatures
                and self.corner_signatures[widget] == signature
            ):
                continue
            self.corner_signatures[widget] = signature
            widget.image = (
                round_document_tile(original, rectangle, outside, radius)
                if touches_corner
                else original
            )

    def fallback_widgets(self) -> list[Markdown | Static]:
        source = self.source
        if self.planning is not None:
            source = (
                "# Planung\n\n## Ziele\n\n"
                + (self.planning.goals_markdown() or "Noch keine Ziele eingetragen.")
                + "\n\n## Verlauf\n"
            )
        widgets: list[Markdown | Static] = [
            Markdown(source, open_links=False, parser_factory=text_document_parser)
        ]
        if self.planning is None:
            return widgets
        if not self.planning.phases:
            widgets.append(Static("Noch kein Verlauf eingetragen.", markup=False))
            return widgets
        table = Table(box=box.SIMPLE_HEAD, expand=True, padding=(0, 1))
        table.add_column("Zeit", no_wrap=True)
        table.add_column("Phase", width=15)
        table.add_column("Inhalt", ratio=1)
        for phase in self.planning.phases:
            time, content = split_phase_time(phase.text)
            markdown = RichMarkdown(content, hyperlinks=False)
            markdown.parsed = text_document_parser().parse(content)
            table.add_row(Text(time), Text(phase.title), markdown)
        widgets.append(Static(table, classes="planning-table"))
        return widgets
