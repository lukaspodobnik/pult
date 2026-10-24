import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from test_ui_integration import prepare_root
from textual.widgets._footer import FooterKey

from pult.app import PultApp
from pult.initialization.school_class import initialize_school_class
from pult.progress.class_progress import get_class_progress_path
from pult.school.school_class import SchoolClass
from pult.school.timetable import TimetableEntry, get_timetable_path, save_timetable
from pult.screens.main_screen import MainScreen
from pult.screens.progress.distribution_screen import DistributionScreen
from pult.services.exports.common import export_path, save_pdf
from pult.views.distribution_view import (
    DistributionView,
)
from pult.widgets.navigation import TeachingPicker, ViewPicker


def test_class_selection_and_export_keep_the_correct_scope(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    initialize_school_class(
        tmp_path, config.active_school_year, SchoolClass("5B", 5, ["mathematik"])
    )
    save_timetable(
        get_timetable_path(tmp_path, config.active_school_year),
        [
            TimetableEntry("monday", 1, "5A", "mathematik", "101"),
            TimetableEntry("wednesday", 1, "5B", "mathematik", "102"),
        ],
    )
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    exports = []

    async def fake_export(renderer, export_config, **kwargs):
        exports.append(kwargs)
        await asyncio.sleep(0.1)
        return tmp_path / "exports/test.pdf"

    monkeypatch.setattr(
        "pult.screens.progress.distribution_screen.export_distribution_plan",
        fake_export,
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause(0.3)
            await pilot.wait_for_scheduled_animations()
            await pilot.pause()
            main = app.screen
            assert isinstance(main, MainScreen)
            classes = main.query_one(ViewPicker)
            classes.highlighted = 2
            await pilot.pause(0.3)
            assert main.active_school_class_id == "5B"
            teaching = main.query_one(TeachingPicker)
            teaching.highlighted = teaching.get_option_index("distribution")
            teaching.focus()
            await pilot.press("enter")
            await pilot.pause(0.3)
            screen = app.screen
            assert isinstance(screen, DistributionScreen)
            assert screen.subject_id == "mathematik"
            picker = screen.query_one(ViewPicker)
            assert picker.highlighted == 1
            assert "5B" in str(screen.query_one("#distribution-content").border_title)
            displayed_rows = next(
                view.rows for view in screen.query(DistributionView) if view.display
            )
            await pilot.press("x")
            screen.action_export_pdf()  # Ein laufender Export wird nicht doppelt gestartet.
            screen.action_export_all_pdf()
            picker.highlighted = 0
            await pilot.pause(0.3)
            assert len(exports) == 1
            assert exports[0]["school_class_id"] == "5B"
            assert exports[0]["rows"] == displayed_rows
            assert not screen._exporting
            assert "5A" in str(screen.query_one("#distribution-content").border_title)
            view = next(view for view in screen.query(DistributionView) if view.display)
            assert all(
                row.date.weekday() == 0 for row in view.rows if row.period is not None
            )
            await pilot.press("escape")
            assert app.screen is main

    asyncio.run(run())


@pytest.mark.parametrize("multiple_subjects", [False, True])
def test_uppercase_x_writes_separate_files_and_keeps_navigation(
    tmp_path, monkeypatch, multiple_subjects
):
    config = prepare_root(tmp_path)
    additional = (
        [SchoolClass("9B", 9, ["mathematik", "informatik-ntg"])]
        if multiple_subjects
        else [SchoolClass(f"5{suffix}", 5, ["mathematik"]) for suffix in "BCDEFGH"]
    )
    for school_class in additional:
        initialize_school_class(tmp_path, config.active_school_year, school_class)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            await app.push_screen(DistributionScreen("5A", subject_id="mathematik"))
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, DistributionScreen)
            picker = screen.query_one(ViewPicker)
            targets = list(picker.class_subjects_by_option_id.values())
            assert len(targets) == (3 if multiple_subjects else 8)
            footer_key = next(
                key
                for key in screen.query(FooterKey)
                if key.action.rsplit(".", 1)[-1] == "export_all_pdf"
            )
            assert footer_key.key_display == "X"
            assert footer_key.description == "Alle exportieren"

            renderer = app.document_renderer
            monkeypatch.setattr(
                renderer, "resolve_font", AsyncMock(return_value="source-sans-3")
            )
            started, proceed = asyncio.Event(), asyncio.Event()
            documents = []

            async def render(document, **kwargs):
                documents.append(document)
                started.set()
                await proceed.wait()
                return b"%PDF-test"

            monkeypatch.setattr(renderer, "render_pdf", render)
            notify = Mock()
            monkeypatch.setattr(screen, "notify", notify)
            await pilot.press("X")
            await asyncio.wait_for(started.wait(), timeout=2)
            assert screen._exporting
            assert not screen.check_action("export_pdf", ())
            assert not screen.check_action("export_all_pdf", ())
            screen.action_export_pdf()
            screen.action_export_all_pdf()
            picker.highlighted = 1
            await pilot.pause(0.2)
            assert screen._displayed_target == targets[1]
            assert len(documents) == 1
            proceed.set()
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            await pilot.pause()
            assert not screen._exporting
            assert screen._displayed_target == targets[1]
            assert screen.check_action("export_pdf", ())
            assert screen.check_action("export_all_pdf", ())
            assert len(documents) == len(targets)
            expected_paths = {
                export_path(
                    tmp_path,
                    config.active_school_year,
                    "stoffverteilungsplan",
                    school_class_id=class_id,
                    subject_id=subject_id,
                )
                for class_id, subject_id in targets
            }
            assert set((tmp_path / "exports").rglob("*.pdf")) == expected_paths
            assert all(path.read_bytes() == b"%PDF-test" for path in expected_paths)
            subjects = {subject.id: subject.name for subject in screen.subjects}
            for document, (class_id, subject_id) in zip(documents, targets):
                assert (
                    f"<title>Stoffverteilungsplan · {class_id} · {subjects[subject_id]}</title>"
                    in document
                )
            assert f"{len(targets)} PDFs gespeichert:" in notify.call_args.args[0]

    asyncio.run(run())


@pytest.mark.parametrize("failure", ["planning", "render"])
def test_batch_export_reports_failed_class_preserves_file_and_continues(
    tmp_path, monkeypatch, failure
):
    config = prepare_root(tmp_path)
    for class_id in ("5B", "5C"):
        initialize_school_class(
            tmp_path,
            config.active_school_year,
            SchoolClass(class_id, 5, ["mathematik"]),
        )
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    previous = export_path(
        tmp_path,
        config.active_school_year,
        "stoffverteilungsplan",
        school_class_id="5B",
        subject_id="mathematik",
    )
    save_pdf(previous, b"%PDF-previous")

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            await app.push_screen(DistributionScreen("5A", subject_id="mathematik"))
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, DistributionScreen)
            if failure == "planning":
                get_class_progress_path(
                    tmp_path, config.active_school_year, "5B"
                ).write_text("invalid TOML")
            renderer = app.document_renderer
            monkeypatch.setattr(
                renderer, "resolve_font", AsyncMock(return_value="source-sans-3")
            )

            async def render(document, **kwargs):
                if (
                    failure == "render"
                    and "<title>Stoffverteilungsplan · 5B ·" in document
                ):
                    raise OSError("Testfehler beim Rendern")
                return b"%PDF-test"

            monkeypatch.setattr(renderer, "render_pdf", render)
            notify = Mock()
            monkeypatch.setattr(screen, "notify", notify)
            await pilot.press("X")
            await app.workers.wait_for_complete()
            assert not screen._exporting
            assert previous.read_bytes() == b"%PDF-previous"
            for class_id in ("5A", "5C"):
                assert (
                    export_path(
                        tmp_path,
                        config.active_school_year,
                        "stoffverteilungsplan",
                        school_class_id=class_id,
                        subject_id="mathematik",
                    ).read_bytes()
                    == b"%PDF-test"
                )
            message = notify.call_args.args[0]
            assert "2 von 3 PDFs gespeichert:" in message
            assert "5B · Mathematik:" in message
            assert notify.call_args.kwargs["severity"] == "warning"

    asyncio.run(run())
