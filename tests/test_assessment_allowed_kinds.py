import asyncio
from dataclasses import replace
from datetime import date, time

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Input, Select, Static

from pult.app import PultApp
from pult.school.assessment import (
    Assessment,
    AssessmentKind,
    get_assessments_path,
    save_assessments,
)
from pult.school.assessment_requirements import (
    load_assessment_requirements,
    save_assessment_requirements,
)
from pult.screens.edit_assessment_screen import EditAssessmentScreen
from pult.screens.edit_assessments_screen import EditAssessmentsScreen
from pult.services.assessments import (
    allowed_assessment_kinds,
    assessment_kind_issue,
    store_assessment,
)


def restrict(config, kinds):
    entries = load_assessment_requirements(config.root, config.active_school_year)
    save_assessment_requirements(
        config.root,
        config.active_school_year,
        [
            replace(entry, allowed_kinds=kinds, minimums=())
            if (entry.subject_id, entry.grade_level) == ("mathematik", 5)
            else entry
            for entry in entries
        ],
    )


def example():
    return Assessment(
        "test",
        "mathematik",
        AssessmentKind.SCHOOL_EXAM,
        "Test",
        date(2026, 10, 5),
        time(8),
        45,
    )


def test_store_rechecks_rules_and_preserves_invalid_existing(tmp_path):
    config = prepare_root(tmp_path)
    entry = example()
    store_assessment(config, "5A", entry, creating=True)
    path = get_assessments_path(tmp_path, config.active_school_year, "5A")
    before = path.read_bytes()
    restrict(config, (AssessmentKind.IMPROMPTU_TEST, AssessmentKind.ANNOUNCED_TEST))
    assert assessment_kind_issue(config, "5A", entry)
    assert allowed_assessment_kinds(config, "5A", "mathematik") == (
        AssessmentKind.IMPROMPTU_TEST,
        AssessmentKind.ANNOUNCED_TEST,
    )
    with pytest.raises(ValueError, match="nicht erlaubt"):
        store_assessment(config, "5A", entry, creating=False)
    with pytest.raises(ValueError, match="nicht erlaubt"):
        store_assessment(config, "5A", replace(entry, id="new"), creating=True)
    assert path.read_bytes() == before
    store_assessment(
        config, "5A", replace(entry, kind=AssessmentKind.IMPROMPTU_TEST), creating=False
    )
    restrict(config, ())
    assert allowed_assessment_kinds(config, "5A", "mathematik") == ()


def test_ui_marks_existing_and_requires_explicit_correction(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    save_assessments(tmp_path, config.active_school_year, "5A", [example()])
    restrict(config, (AssessmentKind.IMPROMPTU_TEST, AssessmentKind.ANNOUNCED_TEST))
    path = get_assessments_path(tmp_path, config.active_school_year, "5A")
    original = path.read_bytes()
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr("pult.app.get_suggested_school_year", lambda *_: None)

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            await app.push_screen(EditAssessmentsScreen())
            await pilot.pause()
            listing = app.screen
            assert isinstance(listing, EditAssessmentsScreen)
            assert "⚠" in listing.row(listing.entries[0]).plain
            assert "nicht erlaubt" in str(
                listing.query_one("#assessment-details-text", Static).content
            )
            assert path.read_bytes() == original
            await pilot.click("#edit-assessment")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, EditAssessmentScreen)
            messages = []
            monkeypatch.setattr(
                screen, "notify", lambda message, **kwargs: messages.append(message)
            )
            assert screen.query_one("#assessment-kind", Select).value is Select.NULL
            assert "Bisher: Schulaufgabe" in str(
                screen.query_one("#assessment-kind-hint", Static).content
            )
            await pilot.click("#save-assessment")
            await pilot.pause(0.5)
            assert app.screen is screen
            assert path.read_bytes() == original
            screen.query_one("#assessment-kind", Select).value = "ex"
            await pilot.pause()
            screen.query_one("#save-assessment").focus()
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen is listing, messages
            assert not listing.kind_issues[("5A", "test")]
            assert "⚠" not in listing.row(listing.entries[0]).plain
            await pilot.click("#create-assessment")
            await pilot.pause()
            assert app.screen.query_one("#assessment-kind", Select).value == "ex"
            assert app.screen.query_one("#assessment-duration", Input).value == "20"
            await pilot.press("escape")
            restrict(config, ())
            await pilot.click("#create-assessment")
            await pilot.pause()
            assert app.screen.query_one("#assessment-kind", Select).disabled
            assert "Keine erlaubten Arten" in str(
                app.screen.query_one("#assessment-kind-hint", Static).content
            )

    asyncio.run(run())
