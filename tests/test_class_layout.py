import asyncio

import pytest
from test_ui_integration import prepare_root

from schooltools_tui.app import SchooltoolsApp
from schooltools_tui.views.school_class_view import SchoolClassView
from schooltools_tui.widgets.navigation import ManagementPicker, ViewPicker


@pytest.mark.parametrize("size", [(206, 46), (180, 42), (241, 70)])
def test_class_dashboard_alignment(tmp_path, monkeypatch, size):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)

    async def run():
        app = SchooltoolsApp()
        async with app.run_test(size=size) as pilot:
            await pilot.pause(0.3)
            picker = app.screen.query_one(ViewPicker)
            picker.highlighted = 1
            await pilot.pause(0.3)
            view = app.screen.query_one(SchoolClassView)
            overview = view.query_one(".subject-overview")
            sequences = view.query_one(".sequence-list")
            details = view.query_one(".class-details")
            management = app.screen.query_one(ManagementPicker)
            logo = app.screen.query_one("#logo-placeholder")
            assert overview.region.y == logo.region.y
            assert overview.region.height == 4
            assert "5A" in str(overview.border_title)
            assert "Mathematik" in str(overview.border_title)
            assert sequences.region.y == picker.region.y
            assert sequences.region.bottom == management.region.bottom
            assert details.region.y == sequences.region.y
            assert details.region.bottom == sequences.region.bottom
            assert details.region.x > sequences.region.right
            rows = list(view.query(".capacity-row"))
            assert len(rows) == 3
            assert [row.region.height for row in rows[:2]] == [1, 1]
            next_lesson = view.query_one(".class-next-lesson")
            capacity = view.query_one(".lesson-capacity")
            summary = view.query_one(".capacity-summary")
            assert summary.region == capacity.content_region
            assert rows[0].region.y == summary.region.y + 1
            assert rows[1].region.y == rows[0].region.bottom
            assert rows[2].region.y == rows[1].region.bottom + 1
            assert rows[2].region.bottom == summary.region.bottom
            assert (next_lesson.region.y, next_lesson.region.height) == (
                picker.region.y,
                picker.region.height,
            )
            assert (capacity.region.y, capacity.region.height) == (
                management.region.y,
                management.region.height,
            )
            assert len({w.region.right for w in view.query(".capacity-value")}) == 1
            assert not view.query("#school-class-title")
            assert view.query_one("#school-class-content").max_scroll_y == 0
            assert set(app.screen.focus_chain) == {picker, management}
            app.save_screenshot(str(tmp_path / "class-layout.svg"))

    asyncio.run(run())
