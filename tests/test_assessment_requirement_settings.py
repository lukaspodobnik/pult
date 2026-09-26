import asyncio

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Input, Select, SelectionList

from pult.app import PultApp
from pult.school.assessment import AssessmentKind
from pult.school.assessment_requirements import (
    AssessmentCategory,
    get_assessment_requirements_path,
    load_assessment_requirements,
)
from pult.screens.edit_assessment_requirements_screen import (
    AssessmentKindsScreen,
    EditAssessmentRequirementsScreen,
    RequirementRow,
)
from pult.screens.settings_screen import SettingsScreen


@pytest.mark.parametrize("size", [(140, 42), (80, 24)])
def test_requirements_settings_drafts_validation_and_year_scope(
    tmp_path, monkeypatch, size
):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr("pult.app.get_suggested_school_year", lambda *_: None)
    original_path = get_assessment_requirements_path(
        tmp_path, config.active_school_year
    )
    original = original_path.read_bytes()
    target = get_assessment_requirements_path(tmp_path, "2027-2028")

    async def run():
        app = PultApp()
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            await app.push_screen(SettingsScreen())
            await pilot.pause()
            app.screen.query_one("#settings-year", Select).value = "2027-2028"
            app.screen.query_one("#edit-requirements").scroll_visible(animate=False)
            await pilot.pause()
            assert await pilot.click("#edit-requirements")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, EditAssessmentRequirementsScreen)
            assert screen.year == "2027-2028"
            assert screen.query_one("#save-requirements").region.bottom <= size[1]
            row = next(
                row
                for row in screen.query(RequirementRow)
                if (row.entry.subject_id, row.entry.grade_level)
                == ("informatik-ntg", 9)
            )
            screen.query_one("#requirements-subject", Select).value = "informatik-ntg"
            await pilot.pause()
            small = row.query_one(f"#small_written-{row.index}", Input)
            small.value = "-1"
            assert await pilot.click("#save-requirements")
            await pilot.pause()
            assert app.screen is screen
            assert not target.exists()
            assert original_path.read_bytes() == original
            small.value = "3"
            row.query_one("Button").scroll_visible(animate=False)
            await pilot.pause()
            assert await pilot.click(row.query_one("Button"))
            await pilot.pause()
            assert isinstance(app.screen, AssessmentKindsScreen)
            selection = app.screen.query_one(SelectionList)
            selection.deselect(AssessmentKind.YEAR_GROUP_TEST)
            assert await pilot.click("#apply-kinds")
            await pilot.pause()
            assert AssessmentKind.YEAR_GROUP_TEST not in row.kinds
            assert small.value == "3"
            screen.query_one("#requirements-subject", Select).value = "mathematik"
            await pilot.pause()
            math = next(
                row
                for row in screen.query(RequirementRow)
                if (row.entry.subject_id, row.entry.grade_level) == ("mathematik", 5)
            )
            math.query_one(f"#large_written-{math.index}", Input).value = "0"
            screen.query_one("#requirements-subject", Select).value = "informatik-ntg"
            await pilot.pause()
            assert small.value == "3"
            assert await pilot.click("#save-requirements")
            await pilot.pause()
            assert isinstance(app.screen, SettingsScreen)
            entries = load_assessment_requirements(tmp_path, "2027-2028")
            info = next(
                entry
                for entry in entries
                if (entry.subject_id, entry.grade_level) == ("informatik-ntg", 9)
            )
            assert info.minimum_for(AssessmentCategory.SMALL_WRITTEN) == 3
            assert AssessmentKind.YEAR_GROUP_TEST not in info.allowed_kinds
            assert original_path.read_bytes() == original
            saved = target.read_bytes()
            app.screen.query_one("#edit-requirements").scroll_visible(animate=False)
            await pilot.pause()
            assert await pilot.click("#edit-requirements")
            await pilot.pause()
            app.screen.query(Input).first().value = "99"
            await pilot.press("escape")
            assert target.read_bytes() == saved
            await pilot.press("escape")
            assert app.require_config().active_school_year == config.active_school_year

    asyncio.run(run())
