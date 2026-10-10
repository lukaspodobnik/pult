"""Dokumente in lesbarer Originalgröße, mit gemeinsamem Browser und Cache."""

import math
from pathlib import Path

from PIL import Image as PILImage
from textual import work
from textual.widgets import Markdown, Static

from pult.curriculum.material import Lesson
from pult.services import material_rendering as graphics
from pult.services.document_rendering import DocumentRenderer
from pult.widgets.scrolling import Vertical, VerticalScroll


class DocumentPane(VerticalScroll):
    can_focus = True
    can_focus_children = False
    DEFAULT_CSS = """
    DocumentPane {height:1fr; padding:0; background:$surface; border:round $primary; overflow-x:hidden;}
    DocumentPane:focus {border:round $primary-lighten-2;}
    """


class DocumentViewer(Vertical):
    DEFAULT_CSS = """
    DocumentViewer {height:auto; background:$surface; overflow:hidden hidden;}
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
    ):
        super().__init__(classes="document-viewer")
        self.source, self.path, self.directory = source, path, directory
        self.planning = planning
        self.renderer: DocumentRenderer | None = None
        self.signature = None
        self.render_timer = None
        self.text_mode = False

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

    def schedule_render(self):
        if not self.is_mounted or self.content_size.width < 5:
            return
        variables = self.app.get_css_variables()
        colors = tuple(variables[key] for key in ("surface", "foreground", "primary"))
        signature = (self.content_size.width, colors, self.text_mode)
        if signature == self.signature:
            return
        self.signature = signature
        if self.render_timer:
            self.render_timer.stop()
        self.render_timer = self.set_timer(0.2, lambda: self.render_document(signature))

    @work(exclusive=True)
    async def render_document(self, signature):
        width, colors, text_mode = signature
        body = self.query_one("#document-body", Vertical)
        try:
            if graphics.image_widget() is None or text_mode:
                widgets = [Markdown(self.fallback_source(), open_links=False)]
            else:
                cell_width, cell_height = graphics.CELL
                pixel_width = width * cell_width
                if self.renderer is None:
                    renderer = getattr(self.app, "document_renderer", None)
                    if renderer is None:
                        renderer = DocumentRenderer()
                        setattr(self.app, "document_renderer", renderer)
                    self.renderer = renderer
                assert self.renderer is not None
                image_path = await self.renderer.render(
                    self.source,
                    self.path,
                    self.directory,
                    pixel_width,
                    max(15, cell_height * 0.85),
                    *colors,
                    planning=self.planning,
                )
                if not self.is_mounted or signature != self.signature:
                    return
                with PILImage.open(image_path) as image:
                    image = image.convert("RGB")
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
                            {"paper_color": colors[0], "ink_color": colors[1]}
                            if factory.__name__ == "StableSixelImage"
                            else {}
                        )
                        widget = factory(padded, classes="document-tile", **kwargs)
                        widget.styles.height = rows
                        widgets.append(widget)
            if not self.is_mounted or signature != self.signature:
                return
            await body.remove_children()
            await body.mount(*widgets)
        except Exception as error:
            if self.is_mounted and signature == self.signature:
                await body.remove_children()
                status = Static(
                    f"Textansicht · {error}"
                    if isinstance(error, ValueError)
                    else "Textansicht · Grafikdarstellung ist nicht verfügbar (siehe README).",
                    markup=False,
                    classes="document-status",
                )
                status.tooltip = str(error)
                await body.mount(
                    status, Markdown(self.fallback_source(), open_links=False)
                )

    def fallback_source(self) -> str:
        if self.planning is None:
            return self.source
        return (
            "# Planung\n\n## Ziele\n\n"
            + (self.planning.goals_markdown() or "Noch keine Ziele eingetragen.")
            + "\n\n## Verlauf\n\n"
            + self.planning.phases_markdown()
        )
