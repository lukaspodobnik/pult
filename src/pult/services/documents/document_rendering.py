"""Gemeinsamer Offline-Renderer für ganze Markdown-Dokumente und TeX."""

import asyncio
import base64
import hashlib
import html
import io
import os
import re
from collections.abc import Callable
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.dollarmath import dollarmath_plugin
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from playwright.async_api import Page, PdfMargins, async_playwright
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from pult.curriculum.material import Lesson
from pult.services.documents.document_callouts import (
    callouts_plugin,
    resolve_callout_colors,
)
from pult.services.documents.document_figures import FIGURE_STYLES, figures_plugin
from pult.services.documents.document_fonts import (
    avenir_font_faces,
    document_font_stylesheet,
    validate_document_font,
)
from pult.services.documents.document_subtasks import SUBTASK_STYLES, subtasks_plugin
from pult.storage import save_bytes

SEPARATOR_Y = "pult.separator_y"


def highlight_code(code: str, language: str, attributes: str) -> str:
    if not language:
        return ""
    try:
        lexer = get_lexer_by_name(language, stripnl=False, ensurenl=False)
    except ClassNotFound:
        return ""
    formatted = highlight(code, lexer, HtmlFormatter(nowrap=True))
    return f'<pre class="syntax-highlight"><code>{formatted}</code></pre>'


def syntax_stylesheet(background: str) -> str:
    red, green, blue = (int(background[i : i + 2], 16) for i in (1, 3, 5))
    brightness = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    style = "github-dark" if brightness < 128 else "friendly"
    return HtmlFormatter(style=style).get_style_defs(".syntax-highlight")


def parser() -> MarkdownIt:
    md = (
        MarkdownIt("commonmark", {"html": False, "highlight": highlight_code})
        .enable("table")
        .use(dollarmath_plugin)
        .use(callouts_plugin)
        .use(subtasks_plugin)
        .use(figures_plugin)
    )
    md.add_render_rule(
        "math_inline",
        lambda _, tokens, i, opts, env: (
            '<span class="math">\\(' + html.escape(tokens[i].content) + "\\)</span>"
        ),
    )
    md.add_render_rule(
        "math_block",
        lambda _, tokens, i, opts, env: (
            '<div class="math display">\\['
            + html.escape(tokens[i].content)
            + "\\]</div>"
        ),
    )
    return md


def safe_local(target: str, source_path: Path, directory: Path) -> Path:
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        raise ValueError(
            "Nur relative Dateien innerhalb des Unterrichtsordners erlaubt."
        )
    path = (source_path.parent / unquote(parsed.path)).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError("Die Datei liegt außerhalb des Unterrichtsordners.")
    return path


def markdown_html(
    source: str,
    source_path: Path,
    directory: Path,
    *,
    transform: Callable[[list[Token]], list[Token]] | None = None,
) -> str:
    md = parser()
    tokens = md.parse(source)
    if transform is not None:
        tokens = transform(tokens)
    for token in tokens:
        for child in token.children or []:
            if child.type == "image":
                path = safe_local(
                    str(child.attrGet("src") or ""), source_path, directory
                )
                mime = {
                    ".svg": "image/svg+xml",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".webp": "image/webp",
                }.get(path.suffix.lower())
                if not mime:
                    raise ValueError(
                        "Dieses Bildformat wird in der Dokumentansicht nicht unterstützt."
                    )
                child.attrSet(
                    "src",
                    f"data:{mime};base64,"
                    + base64.b64encode(path.read_bytes()).decode(),
                )
    return md.renderer.render(tokens, md.options, {})


def split_phase_time(source: str) -> tuple[str, str]:
    """Eine führende Zeitangabe nur für die Anzeige vom Phasentext trennen."""
    match = re.match(
        r"^(?:\*\*(?P<bold>\d+(?:[,.]\d+)?)(?:[ \t]+Min\.)?\*\*|"
        r"(?P<plain>\d+(?:[,.]\d+)?)[ \t]+Min\.)(?=\s|$)",
        source,
    )
    if match is None:
        return "", source
    time = match["bold"] or match["plain"]
    content = source[match.end() :].lstrip(" \t").lstrip("\r\n")
    return time, content


def document_html(
    source: str,
    source_path: Path,
    directory: Path,
    width: int,
    font_size: float,
    bg: str,
    fg: str,
    accent: str,
    planning: Lesson | None = None,
    *,
    stylesheet: str = "",
    font: str = "source-sans-3",
    callout_colors: tuple[str, str] | None = None,
) -> str:
    for color in (bg, fg, accent):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Ungültige Theme-Farbe.")
    definition, merksatz = callout_colors or resolve_callout_colors(
        bg, {"accent": accent}
    )
    for color in (definition, merksatz):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Ungültige Callout-Farbe.")
    if planning is None:
        body = markdown_html(source, source_path, directory)
    else:

        def fragment(text: str) -> str:
            return markdown_html(text, source_path, directory)

        body = "<h1>Planung</h1><h2>Ziele</h2>" + fragment(
            planning.goals_markdown() or "Noch keine Ziele eingetragen."
        )
        body += "<h2>Verlauf</h2>"
        if planning.phases:
            body += '<table class="phases"><thead><tr><th>Zeit</th><th>Phase</th><th>Inhalt</th></tr></thead><tbody>'
            for phase in planning.phases:
                time, content = split_phase_time(phase.text)
                body += (
                    "<tr><td>"
                    + html.escape(time)
                    + "</td><td>"
                    + html.escape(phase.title)
                    + "</td><td>"
                    + fragment(content)
                    + "</td></tr>"
                )
            body += "</tbody></table>"
        else:
            body += "<p>Noch kein Verlauf eingetragen.</p>"
    return f"""<!doctype html><html lang="de"><meta charset="utf-8">
    <style>
    {syntax_stylesheet(bg)}
    * {{box-sizing:border-box}} html,body {{margin:0;background:{bg};color:{fg}}}
    body {{width:{width}px;font-size:{font_size}px;line-height:1.65;
      -webkit-font-smoothing:antialiased;overflow-wrap:anywhere}}
    article {{width:100%;margin:0;padding:.75em 1em 1.5em}}
    h1,h2,h3,h4,h5,h6 {{line-height:1.22;letter-spacing:-.025em;
      color:{accent};font-weight:600;break-after:avoid}}
    h1 {{font-size:2.05em;margin:0 0 .75em}} h2 {{font-size:1.35em;margin:1.8em 0 .65em}}
    h3 {{font-size:1.08em;margin:1.4em 0 .5em}} p {{margin:.75em 0 1em}}
    strong,b {{font-weight:500}}
    li {{margin:.2em 0}} ul,ol {{padding-left:1.4em}}
    li > p {{margin:.4em 0}}
    li > p:first-child {{margin-top:0}} li > p:last-child {{margin-bottom:0}}
    li > ul,li > ol {{margin:.2em 0}}
    a {{color:{accent};text-decoration:none;border-bottom:1px dotted {accent}}}
    blockquote {{margin:1.2em 0;padding:.15em 1em;border-left:3px solid {accent};
      background:color-mix(in srgb,{accent} 7%,{bg})}}
    .callout-definition {{--callout-color:{definition}}}
    .callout-merksatz {{--callout-color:{merksatz}}}
    blockquote.callout {{padding:.8em 1em;border-left-color:var(--callout-color);
      border-radius:0 .4em .4em 0;
      background:color-mix(in srgb,var(--callout-color) 7%,{bg});break-inside:avoid}}
    .callout > .callout-title {{color:var(--callout-color);font-weight:600;
      line-height:1.35;margin:0 0 .55em}}
    .callout > :last-child {{margin-bottom:0}}
    .callout > .callout-title + p {{margin-top:0}}
    table {{border-collapse:collapse;width:100%;font-size:.88em;line-height:1.5;margin:1.2em 0}}
    td,th {{text-align:left;padding:.7em .8em;border-bottom:1px solid color-mix(in srgb,{fg} 20%,{bg})}}
    .phases td,.phases th {{vertical-align:top}}
    .phases td:first-child,.phases th:first-child {{width:1%;white-space:nowrap;
      font-variant-numeric:tabular-nums}}
    .phases td:first-child {{font-weight:500}}
    .phases td:nth-child(2),.phases th:nth-child(2) {{width:1%;overflow-wrap:normal}}
    .phases td p:first-child {{margin-top:0}} .phases td p:last-child {{margin-bottom:0}}
    th {{color:{accent};font-weight:600}} pre {{padding:1em;white-space:pre-wrap;
      background:color-mix(in srgb,{fg} 6%,{bg});border-radius:5px}}
    pre {{line-height:1.5}}
    .syntax-highlight {{color:{fg};background:color-mix(in srgb,{fg} 6%,{bg})}}
    code {{font-size:.85em}} img {{max-width:100%;height:auto}}
    .display {{overflow-x:auto;margin:.4em 0 .4em 2em;padding:.1em 0}}
    p:has(+ .display) {{margin-bottom:.4em}}
    .display > mjx-container[jax="SVG"][display="true"] {{margin:0;text-align:left}}
    mjx-container[jax="SVG"] {{max-width:100%}}
    hr {{border:0;border-top:1px solid color-mix(in srgb,{fg} 18%,{bg});margin:2em 0}}
    {SUBTASK_STYLES}
    {FIGURE_STYLES}
    {document_font_stylesheet(font)}
    {stylesheet}
    </style><article>{body}</article></html>"""


class DocumentRenderer:
    def __init__(self, cache: Path | None = None, *, stylesheet: str = ""):
        self.stylesheet = stylesheet
        self.generation = 0
        self._avenir_available: bool | None = None
        self.driver = self.browser = None
        self.lock = asyncio.Lock()
        self.cache = (
            cache
            or Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
            / "pult/documents"
        )

    async def ensure_browser(self):
        if self.browser is not None and not self.browser.is_connected():
            self.browser = None
        if self.browser is None:
            if self.driver is None:
                self.driver = await async_playwright().start()
            self.browser = await self.driver.chromium.launch(headless=True)

    async def check_available(self) -> None:
        """Einen echten Bild- und PDF-Test ausführen, ohne Dateien zu speichern."""
        async with self.lock:
            await self.ensure_browser()
            assert self.browser is not None
            page = await self.browser.new_page(viewport={"width": 160, "height": 80})
            try:
                await page.route("**/*", lambda route: route.abort())
                await page.set_content("<p>PULT · Dokumentdarstellung</p>")
                await page.screenshot()
                await page.pdf()
                self._avenir_available = None
                self.generation += 1
            finally:
                await page.close()

    async def reset(self) -> None:
        async with self.lock:
            await self.close()
            self._avenir_available = None
            self.generation += 1

    async def avenir_available(self) -> bool:
        if self._avenir_available is not None:
            return self._avenir_available
        async with self.lock:
            if self._avenir_available is not None:
                return self._avenir_available
            page = None
            try:
                await self.ensure_browser()
                assert self.browser is not None
                page = await self.browser.new_page()
                await page.route("**/*", lambda route: route.abort())
                await page.set_content("<style>" + avenir_font_faces() + "</style>")
                self._avenir_available = await page.evaluate("""async () => {
                    try {
                        for (const style of ['normal', 'italic']) {
                            for (const weight of [400, 500, 600]) {
                                const faces = await document.fonts.load(
                                    `${style} ${weight} 16px "Pult Avenir"`, 'Abc');
                                if (!faces.length || faces.some(f => f.status !== 'loaded'))
                                    return false;
                            }
                        }
                        return true;
                    } catch { return false; }
                }""")
            except Exception:
                # Rendering still provides its existing text fallback if the browser fails.
                self._avenir_available = False
            finally:
                if page is not None:
                    await page.close()
            return bool(self._avenir_available)

    async def resolve_font(self, font: str) -> str:
        validate_document_font(font)
        if font != "source-sans-3" and await self.avenir_available():
            return "avenir-next"
        return "source-sans-3"

    async def render(
        self,
        source: str,
        path: Path,
        directory: Path,
        width: int,
        font_size: float,
        bg: str,
        fg: str,
        accent: str,
        planning: Lesson | None = None,
        *,
        font: str = "auto",
        callout_colors: tuple[str, str] | None = None,
    ) -> Path:
        resolved_font = await self.resolve_font(font)
        document = document_html(
            source,
            path,
            directory,
            width,
            font_size,
            bg,
            fg,
            accent,
            planning,
            stylesheet=self.stylesheet,
            font=resolved_font,
            callout_colors=callout_colors,
        )
        script = Path(__file__).parents[2] / "assets/mathjax/tex-svg-full.js"
        key = hashlib.sha256(
            (document + str(script.stat().st_mtime_ns) + "separator-v1").encode()
        ).hexdigest()
        target = self.cache / f"{key}.png"
        # Warm documents must not wait behind a background render in Chromium.
        if target.exists():
            return target
        async with self.lock:
            if target.exists():
                return target
            await self.ensure_browser()
            assert self.browser is not None
            page = await self.browser.new_page(
                viewport={"width": width, "height": 1}, device_scale_factor=1
            )
            rendering = asyncio.create_task(self._render_png(page, document, target))
            try:
                return await asyncio.shield(rendering)
            finally:
                # Closing the page aborts an obsolete render. Drain its result
                # without cancelling a pending Playwright protocol callback.
                await asyncio.shield(
                    asyncio.gather(page.close(), rendering, return_exceptions=True)
                )

    async def _render_png(self, page: Page, document: str, target: Path) -> Path:
        # Offline rendering: never fetch links, remote images, or extra scripts.
        await page.route("**/*", lambda route: route.abort())
        await page.set_content(document, wait_until="load")
        await self._prepare_page(page, math=True)
        self.cache.mkdir(parents=True, exist_ok=True)
        separator_y = await page.evaluate("""() => {
            const rule = document.querySelector('article > hr');
            return rule ? rule.getBoundingClientRect().top + scrollY : null;
        }""")
        screenshot = await page.screenshot(full_page=True, timeout=30000)
        if separator_y is not None:
            # Keep the measured position with the cached pixels so a cache
            # hit needs no browser layout pass to find the continuation.
            metadata = PngInfo()
            metadata.add_text(SEPARATOR_Y, str(separator_y))
            with Image.open(io.BytesIO(screenshot)) as image:
                output = io.BytesIO()
                image.save(output, format="PNG", pnginfo=metadata)
                screenshot = output.getvalue()
        save_bytes(target, screenshot)

        return target

    @staticmethod
    async def _prepare_page(
        page: Page, *, math: bool = False, strict_math: bool = False
    ) -> None:
        if math:
            script = Path(__file__).parents[2] / "assets/mathjax/tex-svg-full.js"
            await page.evaluate(
                """strict => {
                window.MathJax = {startup:{typeset:false},
                    tex:{inlineMath:[['\\\\(','\\\\)']],displayMath:[['\\\\[','\\\\]']]},
                    svg:{fontCache:'local'}};
                if (strict) MathJax.tex.packages = {'[-]':['noerrors','noundefined']};
            }""",
                strict_math,
            )
            await page.add_script_tag(content=script.read_text())
            await page.evaluate(
                "async () => {await MathJax.startup.promise; "
                "await MathJax.typesetPromise(); await document.fonts.ready;}"
            )
            if await page.locator('[data-mml-node="merror"]').count():
                raise ValueError("Mindestens eine Formel konnte nicht gesetzt werden.")
            await page.evaluate(
                "async () => {await Promise.all(Array.from(document.images,"
                "i => i.decode()));}"
            )
        else:
            await page.evaluate(
                "async () => {await document.fonts.ready; "
                "await Promise.all(Array.from(document.images, i => i.decode()));}"
            )

    async def render_pdf(
        self,
        document: str,
        *,
        font: str = "source-sans-3",
        math: bool = False,
        margins: PdfMargins | None = None,
        header_template: str | None = None,
        footer_template: str | None = None,
        prepare_script: str | None = None,
    ) -> bytes:
        """HTML offline als durchsuchbare A4-PDF mit Seitenzahlen drucken."""
        footer_styles = document_font_stylesheet(font)
        footer_family = (
            "'Avenir Next',sans-serif"
            if font == "avenir-next"
            else "'Pult Source Sans',sans-serif"
        )
        async with self.lock:
            await self.ensure_browser()
            assert self.browser is not None
            page = await self.browser.new_page()
            try:
                await page.route("**/*", lambda route: route.abort())
                await page.emulate_media(media="print")
                await page.set_content(document, wait_until="load")
                await self._prepare_page(page, math=math, strict_math=True)
                if prepare_script is not None:
                    layout_error = await page.evaluate(prepare_script)
                    if layout_error:
                        raise ValueError(str(layout_error))
                return await page.pdf(
                    format="A4",
                    prefer_css_page_size=True,
                    print_background=True,
                    margin=margins
                    or {
                        "top": "14mm",
                        "bottom": "18mm",
                        "left": "12mm",
                        "right": "12mm",
                    },
                    display_header_footer=True,
                    header_template=header_template
                    if header_template is not None
                    else "<span></span>",
                    footer_template=footer_template
                    if footer_template is not None
                    else (
                        f"<style>{footer_styles}</style>"
                        f'<div style="font-family:{footer_family};font-size:9px;font-weight:400;'
                        'color:#59616a;width:100%;text-align:center">'
                        '<span class="pageNumber"></span> / '
                        '<span class="totalPages"></span></div>'
                    ),
                )
            finally:
                await page.close()

    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.driver:
            await self.driver.stop()
            self.driver = None
