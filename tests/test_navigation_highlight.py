import asyncio

import pytest
from test_daily_highlight_redraw import data_files
from test_ui_integration import prepare_root

from pult.app import PultApp
from pult.screens.main_screen import MainScreen
from pult.widgets.navigation import ManagementPicker, TeachingPicker, ViewPicker
from pult.widgets.scrolling import OptionList


def navigation_state(screen):
    return [
        (
            picker,
            tuple(id(option) for option in picker.options),
            picker.highlighted,
            picker.scroll_offset,
        )
        for picker in screen.query_one("#navigation").query(OptionList)
    ]


def assert_selected_background(picker, *, focused):
    assert picker.has_focus is focused
    assert picker.highlighted is not None
    label = str(picker.get_option_at_index(picker.highlighted).prompt)
    styles = [
        segment.style
        for strip in picker.render_lines(picker.size.region)
        for segment in strip
        if label in segment.text
    ]
    assert styles, label
    normal_background = picker.background_colors[1].rich_color
    for style in styles:
        assert style is not None
        assert (style.bgcolor != normal_background) is focused
        assert bool(style.bold) is focused


@pytest.mark.parametrize("width", [160, 179])
def test_startup_highlight_is_visible_without_mouse_or_selection_change(
    tmp_path, monkeypatch, logging_session, width
):
    root = tmp_path / "unterricht"
    root.mkdir()
    config = prepare_root(root)
    before_files = data_files(root)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.delenv("NO_COLOR", raising=False)
    before_redraw = {}
    finish_startup = MainScreen._finish_startup

    def record_startup_state(screen):
        before_redraw["navigation"] = navigation_state(screen)
        before_redraw["focus"] = screen.app.focused
        finish_startup(screen)

    monkeypatch.setattr(MainScreen, "_finish_startup", record_startup_state)

    async def run():
        # Use the normal startup animation, without a special debug mode or
        # any interaction that might incidentally repair the style cache.
        app = PultApp()
        async with app.run_test(size=(width, 45)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            await pilot.pause()
            main = app.screen
            assert not main.startup_active
            assert main.query_one("#main").styles.opacity == 1
            assert navigation_state(main) == before_redraw["navigation"]
            assert app.focused is before_redraw["focus"]
            picker = main.query_one(ViewPicker)
            assert picker.get_option_at_index(picker.highlighted).id == "home"
            assert main.active_school_class_id is None
            assert main._pending_view_id is None
            assert_selected_background(picker, focused=True)
            assert_selected_background(main.query_one(TeachingPicker), focused=False)
            assert_selected_background(main.query_one(ManagementPicker), focused=False)
            text = logging_session.path.read_text()
            assert text.count("navigation_redraw_requested") == 3

            # Hovering and leaving must keep the selected option highlighted.
            await pilot.hover(picker, offset=(3, 1))
            await pilot.hover("#content", offset=(4, 4))
            await pilot.pause()
            assert_selected_background(picker, focused=True)
            assert navigation_state(main) == before_redraw["navigation"]

            for expected in (TeachingPicker, ManagementPicker, ViewPicker):
                await pilot.press("tab")
                await pilot.pause()
                assert isinstance(app.focused, expected)
                for kind in (ViewPicker, TeachingPicker, ManagementPicker):
                    assert_selected_background(
                        main.query_one(kind), focused=kind is expected
                    )
            assert (
                logging_session.path.read_text().count("navigation_redraw_requested")
                == 3
            )

    asyncio.run(run())
    assert data_files(root) == before_files
