import asyncio
from dataclasses import replace
from datetime import date, time

from test_ui_integration import prepare_root
from textual.widgets import Input

from pult.app import PultApp
from pult.initialization.school_class import initialize_school_class
from pult.school.assessment import (
    Assessment,
    AssessmentKind,
    load_assessments,
    save_assessments,
)
from pult.school.calendar import (
    Closure,
    ClosureKind,
    load_school_calendar,
    save_class_closures,
    save_school_closures,
)
from pult.school.school_class import SchoolClass
from pult.screens.edit_assessment_screen import EditAssessmentScreen
from pult.screens.edit_assessments_screen import EditAssessmentsScreen
from pult.screens.edit_closures_screen import EditClosuresScreen
from pult.services.assessment_conflicts import assessment_conflicts, closure_conflicts
from pult.services.closures import ScopedClosure


def sample():
    return Assessment(
        "test",
        "mathematik",
        AssessmentKind.SCHOOL_EXAM,
        "Brüche",
        date(2026, 10, 5),
        time(8),
        45,
    )


def test_conflicts_respect_scope_boundaries_and_completion(tmp_path):
    config = prepare_root(tmp_path)
    initialize_school_class(
        config.root, config.active_school_year, SchoolClass("6B", 6, ["mathematik"])
    )
    entry = sample()
    closure = Closure("Wandertag", ClosureKind.LOCAL, entry.date, entry.date)
    for class_id in ("5A", "6B"):
        save_assessments(config.root, config.active_school_year, class_id, [entry])
    save_class_closures(config.root, config.active_school_year, "5A", [closure])
    assert assessment_conflicts(config, "5A", entry) == (closure,)
    assert not assessment_conflicts(config, "6B", entry)
    assert not assessment_conflicts(
        config, "5A", replace(entry, date=date(2026, 10, 6))
    )
    assert [
        item.school_class_id
        for item in closure_conflicts(config, ScopedClosure(closure, "5A"))
    ] == ["5A"]
    assert len(closure_conflicts(config, ScopedClosure(closure, None))) == 2
    completed = replace(entry, completed_on=entry.date)
    save_assessments(config.root, config.active_school_year, "5A", [completed])
    loaded = load_assessments(config.root, config.active_school_year, "5A")[0]
    assert loaded == completed
    assert not assessment_conflicts(config, "5A", loaded)
    assert [
        item.school_class_id
        for item in closure_conflicts(config, ScopedClosure(closure, None))
    ] == ["6B"]
    holiday = load_school_calendar(config.root, config.active_school_year).closures[0]
    assert holiday in assessment_conflicts(
        config, "6B", replace(entry, date=holiday.start)
    )


def test_ui_warns_from_both_sides_and_clears_marker(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    entry = sample()
    closure = Closure("Wandertag", ClosureKind.LOCAL, entry.date, entry.date)
    save_assessments(config.root, config.active_school_year, "5A", [entry])

    async def run():
        app = PultApp()
        notices = []
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            monkeypatch.setattr(
                app,
                "notify",
                lambda message, **kwargs: notices.append((message, kwargs)),
            )
            closures = EditClosuresScreen()
            await app.push_screen(closures)
            await pilot.pause()
            closures.closure_created(ScopedClosure(closure, None))
            await pilot.pause()
            assert any(
                "Wandertag" in message
                and "5A" in message
                and kwargs.get("severity") == "warning"
                for message, kwargs in notices
            )
            screen = EditAssessmentsScreen()
            await app.push_screen(screen)
            await pilot.pause()
            assert "⚠" in screen.row(screen.entries[0]).plain
            assert "Wandertag" in str(
                screen.query_one("#assessment-details-text").render()
            )
            screen.action_create()
            await pilot.pause()
            form = app.screen
            assert isinstance(form, EditAssessmentScreen)
            form.query_one("#assessment-title", Input).value = "Externer Test"
            form.query_one("#assessment-date", Input).value = "05.10.2026"
            notices.clear()
            form.save()
            await pilot.pause()
            assert app.screen is screen
            assert len(screen.entries) == 2
            assert any(
                "Externer Test" in message and kwargs.get("severity") == "warning"
                for message, kwargs in notices
            )
            # Verschieben entfernt nur den Konflikt des verschobenen Termins.
            screen.action_edit()
            await pilot.pause()
            form = app.screen
            form.query_one("#assessment-date", Input).value = "06.10.2026"
            form.save()
            await pilot.pause()
            assert sum("⚠" in screen.row(item).plain for item in screen.entries) == 1
            save_school_closures(config.root, config.active_school_year, [])
            screen.reload_entries()
            assert not any("⚠" in screen.row(item).plain for item in screen.entries)

    asyncio.run(run())
