import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
import tomli_w
from test_ui_integration import prepare_root
from textual.widgets import Input

from pult.app import PultApp
from pult.screens.progress.cancel_lesson_screen import CancelLessonScreen
from pult.services.omarchy_theme import (
    OmarchyThemeWatcher,
    theme_from_palette,
)


@pytest.fixture
def palette():
    return dict(
        mode="dark",
        background="#2c2525",
        foreground="#e6d9db",
        accent="#f38d70",
        selection="#403e41",
        muted="#72696a",
        green="#adda78",
        yellow="#f9cc6c",
        red="#fd6883",
    )


def write_palette(path, palette):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(palette))


@pytest.mark.parametrize(
    "key,value",
    [("accent", "red"), ("background", 42), ("green", None), ("mode", "wrong")],
)
def test_reject_invalid_palette(palette, key, value):
    with pytest.raises(ValueError):
        theme_from_palette(palette | {key: value})


def test_watcher_replacement_errors_and_unchanged_file(tmp_path, palette):
    path = tmp_path / "current" / "colors.toml"
    watcher = OmarchyThemeWatcher(path)
    assert watcher.poll() is None
    write_palette(path, palette)
    assert watcher.poll().primary == palette["accent"]
    with patch.object(Path, "open", side_effect=AssertionError("Unnötiges Neuladen")):
        assert watcher.poll() is None
    write_palette(path, palette)
    assert watcher.poll() is None  # Nur Zeitstempel geändert.
    path.write_text("accent = [")
    assert watcher.poll() is None
    assert watcher.last_error
    path.unlink()
    assert watcher.poll() is None
    write_palette(path, palette | {"accent": "#123456"})
    assert watcher.poll().primary == "#123456"
    assert watcher.last_error is None
    # Wie bei Omarchy: das gesamte aktive Verzeichnis ersetzen.
    path.parent.rename(tmp_path / "previous")
    write_palette(path, palette)
    assert watcher.poll().primary == palette["accent"]
    with patch.object(Path, "stat", side_effect=PermissionError("Kein Zugriff")):
        assert watcher.poll() is None


def test_theme_reload_preserves_unsaved_input(tmp_path, monkeypatch, palette):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    path = tmp_path / "omarchy" / "colors.toml"

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            await app.push_screen(CancelLessonScreen("5A"))
            await pilot.pause()
            modal = app.screen
            field = modal.query_one(Input)
            field.value = "Noch nicht gespeichert"
            field.focus()
            field.cursor_position = 5
            write_palette(path, palette | {"accent": "#88c0d0"})
            await pilot.pause(1.2)
            assert app.current_theme.primary == "#88c0d0"
            assert app.screen is modal
            assert app.focused is field
            assert field.value == "Noch nicht gespeichert"
            assert field.cursor_position == 5

    asyncio.run(run())
