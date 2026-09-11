import asyncio
from pathlib import Path

from app import Material, UnterrichtApp, load_lessons
from PIL import Image
from rendering import blocks, formula_image, prepare_assets


def test_parser_keeps_code_and_extracts_math():
    source = (
        '```python\ntext = "$$no math$$"\n```\n\nA $x^2$ B.\n\n$$\n\\frac{2}{3}\n$$\n'
    )
    parsed = list(blocks(source))
    assert [kind for kind, _, _ in parsed] == ["text", "inline", "text", "math"]
    assert "$$no math$$" in parsed[0][1]
    assert parsed[1][1][1].type == "math_inline"


def test_assets_and_aligned():
    prepare_assets(load_lessons())
    with Image.open(
        formula_image(r"\begin{aligned}2x+4&=10\\2x&=6\\x&=3\end{aligned}")
    ) as image:
        assert image.height > 70
        assert image.width > 60


def test_sixel_palette():
    from sixel import terminal_safe_sixel

    raw = '\x1bP0;0;0q"1;1;4;6#0;2;0;0;0??#1;2;100;100;100@@\x1b\\'
    result = terminal_safe_sixel(raw)
    assert result.startswith('\x1bP0;1;0q"1;1;4;6#0;2;0;0;0#1;2;100;100;100')
    assert result.endswith("#0??#1@@\x1b\\")


def test_navigation_and_order():
    async def check():
        app = UnterrichtApp()
        async with app.run_test(size=(180, 52)) as pilot:
            await pilot.pause()
            assert app.query_one("#orientation").display
            assert app.query_one("#preparation").display
            assert not app.query_one("#tasks").display
            children = list(app.query_one("#tasks").children)
            assert children[0].has_class("task-title")
            assert isinstance(children[1], Material)
            assert children[2].has_class("solution-title")
            assert isinstance(children[3], Material)
            assert app.query_one("#goals").region.y == 1
            assert app.query_one("#preparation").region.y == 1
            listing = app.query_one("#lesson-list")
            assert listing.option_count == 2
            listing.focus()
            await pilot.press("down", "enter")
            await pilot.pause()
            assert app.lesson["title"] == "Brüche kürzen"
            await app.open_lesson(0)
            await pilot.pause(1)
            assert "Brüche erweitern" in listing.render_line(0).text
            assert app.query_one("#preparation .inline-flow").children
            app.save_screenshot("preview.svg", path=Path(__file__).parent)
            await pilot.press("space")
            assert app.query_one("#tasks").display
            await pilot.press("tab")
            assert app.focused.id == "goals"
            await pilot.press("b", "b")
            await pilot.pause()
            assert app.lesson["title"] == "Eine Zahl erraten"
            assert app.query("MarkdownFence")
            await pilot.press("space")
            await pilot.pause()
            app.save_screenshot("preview-code.svg", path=Path(__file__).parent)
            await pilot.press("q")

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(check())
    finally:
        loop.close()


def test_graphics_mount():
    from sixel import StableSixelImage

    async def check():
        app = UnterrichtApp(image_widget=StableSixelImage)
        async with app.run_test(size=(180, 52)) as pilot:
            await pilot.pause()
            assert app.query(".formula")
            assert app.query(".inline-text")
            await pilot.press("space", "b", "space")
            await pilot.pause()
            assert app.query(".formula")
            await pilot.press("q")

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(check())
    finally:
        loop.close()
