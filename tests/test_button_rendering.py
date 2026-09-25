import asyncio

from textual.app import App
from textual.geometry import Region
from textual.widgets import Input

from pult.widgets.button import Button


def test_button_highlight_stays_inside_frame():
    class TestApp(App):
        CSS_PATH = "../src/pult/styles/app.tcss"

        def compose(self):
            yield Input()
            yield Button("Speichern")

    async def run():
        app = TestApp()
        async with app.run_test() as pilot:
            button = app.query_one(Button)
            for state in ("normal", "focus", "hover", "active", "disabled"):
                if state == "focus":
                    button.focus()
                elif state == "hover":
                    app.query_one(Input).focus()
                    await pilot.hover(button)
                elif state == "active":
                    button.add_class("-active")
                elif state == "disabled":
                    button.remove_class("-active")
                    button.disabled = True
                await pilot.pause()
                lines = button.render_lines(
                    Region(0, 0, button.region.width, button.region.height)
                )
                background = list(lines[0])[0].style.bgcolor
                assert len(lines) == 3
                assert lines[0].text.startswith("╭")
                assert lines[0].text.endswith("╮")
                assert all(
                    segment.style.bgcolor == background
                    for line in (lines[0], lines[-1])
                    for segment in line
                ), state
                middle = list(lines[1])
                assert middle[0].style.bgcolor == background, state
                assert middle[-1].style.bgcolor == background, state
                assert "Speichern" in lines[1].text
                assert all(
                    (segment.style.bgcolor != background)
                    == (state in {"focus", "hover", "active"})
                    for segment in middle[1:-1]
                ), state

    asyncio.run(run())
