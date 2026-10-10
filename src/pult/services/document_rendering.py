"""Gemeinsamer Offline-Renderer für ganze Markdown-Dokumente und TeX."""

import asyncio
import base64
import hashlib
import html
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
from playwright.async_api import async_playwright

from pult.curriculum.material import Lesson


def parser() -> MarkdownIt:
    md = (
        MarkdownIt("commonmark", {"html": False}).enable("table").use(dollarmath_plugin)
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


def markdown_html(source: str, source_path: Path, directory: Path) -> str:
    md = parser()
    tokens = md.parse(source)
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
) -> str:
    for color in (bg, fg, accent):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Ungültige Theme-Farbe.")
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
            body += '<table class="phases"><thead><tr><th>Phase</th><th>Inhalt</th></tr></thead><tbody>'
            body += "".join(
                "<tr><td>"
                + html.escape(p.title)
                + "</td><td>"
                + fragment(p.text)
                + "</td></tr>"
                for p in planning.phases
            )
            body += "</tbody></table>"
        else:
            body += "<p>Noch kein Verlauf eingetragen.</p>"
    return f"""<!doctype html><html lang="de"><meta charset="utf-8">
    <style>
    * {{box-sizing:border-box}} html,body {{margin:0;background:{bg};color:{fg}}}
    body {{width:{width}px;font: {font_size}px/1.65 Georgia,"Times New Roman",serif;
      -webkit-font-smoothing:antialiased;overflow-wrap:anywhere}}
    article {{width:100%;margin:0;padding:.75em 1em 1.5em}}
    h1,h2,h3 {{font-family:Arial,sans-serif;line-height:1.22;letter-spacing:-.025em;
      color:{accent};font-weight:600;break-after:avoid}}
    h1 {{font-size:2.05em;margin:0 0 .75em}} h2 {{font-size:1.35em;margin:1.8em 0 .65em}}
    h3 {{font-size:1.08em;margin:1.4em 0 .5em}} p {{margin:.75em 0 1em}}
    li {{margin:.35em 0}} ul,ol {{padding-left:1.4em}}
    a {{color:{accent};text-decoration:none;border-bottom:1px dotted {accent}}}
    blockquote {{margin:1.2em 0;padding:.15em 1em;border-left:3px solid {accent};
      background:color-mix(in srgb,{accent} 7%,{bg})}}
    table {{border-collapse:collapse;width:100%;font: .88em/1.5 Arial,sans-serif;margin:1.2em 0}}
    td,th {{text-align:left;padding:.7em .8em;border-bottom:1px solid color-mix(in srgb,{fg} 20%,{bg})}}
    .phases td:first-child,.phases th:first-child {{width:20%;vertical-align:top}}
    .phases td p:first-child {{margin-top:0}} .phases td p:last-child {{margin-bottom:0}}
    th {{color:{accent};font-weight:600}} pre {{padding:1em;white-space:pre-wrap;
      background:color-mix(in srgb,{fg} 6%,{bg});border-radius:5px}}
    code {{font-family:monospace;font-size:.85em}} img {{max-width:100%;height:auto}}
    .display {{overflow-x:auto;padding:.2em 0}} mjx-container[jax="SVG"] {{max-width:100%}}
    hr {{border:0;border-top:1px solid color-mix(in srgb,{fg} 18%,{bg});margin:2em 0}}
    </style><article>{body}</article></html>"""


class DocumentRenderer:
    def __init__(self, cache: Path | None = None):
        self.driver = self.browser = None
        self.lock = asyncio.Lock()
        self.cache = (
            cache
            or Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
            / "pult/documents"
        )

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
    ) -> Path:
        document = document_html(
            source, path, directory, width, font_size, bg, fg, accent, planning
        )
        script = Path(__file__).parents[1] / "assets/mathjax/tex-svg-full.js"
        key = hashlib.sha256(
            (document + str(script.stat().st_mtime_ns)).encode()
        ).hexdigest()
        target = self.cache / f"{key}.png"
        async with self.lock:
            if target.exists():
                return target
            if self.browser is None:
                self.driver = await async_playwright().start()
                self.browser = await self.driver.chromium.launch(headless=True)
            page = await self.browser.new_page(
                viewport={"width": width, "height": 1}, device_scale_factor=1
            )
            try:
                # Offline rendering: never fetch links, remote images, or extra scripts.
                await page.route("**/*", lambda route: route.abort())
                await page.set_content(document, wait_until="load")
                await page.evaluate("""window.MathJax = {startup:{typeset:false},
                    tex:{inlineMath:[['\\\\(','\\\\)']],displayMath:[['\\\\[','\\\\]']]},
                    svg:{fontCache:'local'}}""")
                await page.add_script_tag(content=script.read_text())
                await page.evaluate(
                    "async () => {await MathJax.startup.promise; "
                    "await MathJax.typesetPromise(); await document.fonts.ready;}"
                )
                if await page.locator('[data-mml-node="merror"]').count():
                    raise ValueError(
                        "Mindestens eine Formel konnte nicht gesetzt werden."
                    )
                await page.evaluate(
                    "async () => {await Promise.all(Array.from(document.images,"
                    "i => i.decode()));}"
                )
                self.cache.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(".tmp.png")
                await page.screenshot(
                    path=str(temporary), full_page=True, timeout=30000
                )
                temporary.replace(target)

                return target
            finally:
                await page.close()

    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.driver:
            await self.driver.stop()
            self.driver = None
