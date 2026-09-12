import asyncio

import pytest
from test_ui_integration import prepare_root

from pult.app import PultApp
from pult.views.school_class_view import SchoolClassView
from pult.widgets.navigation import ManagementPicker, TeachingPicker, ViewPicker


@pytest.mark.parametrize("size", [(206, 46), (180, 42), (241, 70)])
def test_class_dashboard_alignment(tmp_path, monkeypatch, size):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=size) as pilot:
            await pilot.pause(0.3)
            picker = app.screen.query_one(ViewPicker)
            picker.highlighted = 1
            await pilot.pause(0.3)
            for _ in range(40):
                if app.screen._pending_view_id is None:
                    break
                await pilot.pause(0.05)
            await pilot.pause()
            view = app.screen.query_one(SchoolClassView)
            footer = app.screen.query_one("PultFooter")
            keys = list(footer.query("FooterKey"))
            assert keys[0].action.rsplit(".", 1)[-1] == "go_home"
            assert footer.query_one(".help-key").display
            assert (
                footer.query_one(".quit-key").region.right
                == footer.content_region.right
            )
            assert all(key.region.right <= footer.content_region.right for key in keys)
            overview = view.query_one(".subject-overview")
            sequences = view.query_one(".sequence-list")
            details = view.query_one(".class-details")
            management = app.screen.query_one(ManagementPicker)
            teaching = app.screen.query_one(TeachingPicker)
            logo = app.screen.query_one("#app-logo")
            assert overview.region.y == logo.region.y + 1
            first_sequence = view.query_one(".sequence-progress")
            assert first_sequence.styles.margin.top == 0
            assert first_sequence.styles.padding.top == 0
            assert first_sequence.styles.padding.bottom == 0
            assert overview.region.height == 4
            assert "5A" in str(overview.border_title)
            assert "Mathematik" in str(overview.border_title)
            assert sequences.region.y == picker.region.y
            assert sequences.region.bottom <= management.region.bottom
            assert details.region.y == sequences.region.y
            assert details.region.bottom == management.region.bottom
            assert details.region.x == sequences.region.x
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
            assert next_lesson.region.y == picker.region.y
            assert next_lesson.region.bottom == details.region.bottom
            assert next_lesson.region.x >= details.region.right
            assert sequences.region.bottom == teaching.region.bottom
            assert capacity.region.y == management.region.y
            assert capacity.region.bottom <= management.region.bottom
            assert len({w.region.right for w in view.query(".capacity-value")}) == 1
            assert not view.query("#school-class-title")
            assert view.query_one("#school-class-content").max_scroll_y == 0
            assert set(app.screen.focus_chain) == {picker, teaching, management}
            app.save_screenshot(str(tmp_path / "class-layout.svg"))

    asyncio.run(run())
