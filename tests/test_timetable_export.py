import asyncio
from datetime import datetime, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from test_ui_integration import prepare_root

from pult.app import PultApp
from pult.config import AppConfig
from pult.school.period import Period
from pult.school.timetable import TimetableEntry, get_timetable_path, save_timetable
from pult.screens.management.edit_timetable_screen import EditTimetableScreen
from pult.services.exports.timetable_export import export_timetable, timetable_html


def test_weekly_pdf_includes_all_periods_and_escapes_content():
    periods = tuple(Period(i, time(7 + i, 0), time(7 + i, 45)) for i in range(1, 12))
    entries = (
        TimetableEntry("monday", 1, "7D", "mathematik", "101 & 102"),
        TimetableEntry("friday", 11, "9A", "informatik", "<Computerraum>"),
    )
    document = timetable_html(
        entries,
        periods,
        {"mathematik": "Ma", "informatik": "Inf"},
        school_year="2026-2027",
        generated_at=datetime(2026, 10, 11, 10, 30),
    )
    assert "A4 landscape" in document
    assert document.count('<th scope="col">') == 6
    assert document.count('<th scope="row">') == 11
    assert "Montag" in document and "Freitag" in document
    assert "7D · Ma" in document and "9A · Inf" in document
    assert "101 &amp; 102" in document and "&lt;Computerraum&gt;" in document
    assert "11. Stunde" in document and "18:00–18:45" in document
    assert "Stand: 11.10.2026, 10:30" in document
    assert document.count('<td class="empty">') == 53


def test_export_uses_shared_overview_path_and_resolved_font(tmp_path):
    config = AppConfig(tmp_path, "editor", "2026-2027")
    renderer = SimpleNamespace(
        resolve_font=AsyncMock(return_value="avenir-next"),
        render_pdf=AsyncMock(return_value=b"%PDF-test"),
    )
    target = asyncio.run(
        export_timetable(renderer, config, entries=(), periods=(), subject_labels={})
    )
    assert target == tmp_path / "exports/2026-2027/uebersichten/stundenplan.pdf"
    assert target.read_bytes() == b"%PDF-test"
    assert renderer.render_pdf.call_args.kwargs["font"] == "avenir-next"
    assert "Keine Stundenzeiten konfiguriert." in renderer.render_pdf.call_args.args[0]


def test_timetable_export_hotkey_snapshot_and_error_recovery(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    save_timetable(
        get_timetable_path(tmp_path, config.active_school_year),
        [TimetableEntry("monday", 1, "5A", "mathematik", "101")],
    )
    captures = []
    export_ready = asyncio.Event()

    async def fake_export(renderer, export_config, **kwargs):
        captures.append(kwargs)
        await export_ready.wait()
        if len(captures) == 2:
            raise OSError("Schreibfehler")
        return tmp_path / "exports/2026-2027/uebersichten/stundenplan.pdf"

    monkeypatch.setattr(
        "pult.screens.management.edit_timetable_screen.export_timetable", fake_export
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            screen = EditTimetableScreen()
            await app.push_screen(screen)
            await pilot.pause()
            notify = Mock()
            monkeypatch.setattr(screen, "notify", notify)
            await pilot.press("x")
            screen.action_export_pdf()
            screen.entries_by_slot[("monday", 1)].room = "202"
            export_ready.set()
            await pilot.pause(0.3)
            assert len(captures) == 1
            assert captures[0]["entries"][0].room == "101"
            assert len(captures[0]["periods"]) == len(screen.periods)
            assert not screen._exporting
            assert "PDF gespeichert:" in notify.call_args.args[0]
            await pilot.press("x")
            await pilot.pause(0.3)
            assert len(captures) == 2 and not screen._exporting
            notify.assert_called_with(
                "Der PDF-Export ist fehlgeschlagen: Schreibfehler", severity="error"
            )

    asyncio.run(run())
