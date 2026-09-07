import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
import tomli_w
from test_ui_integration import prepare_root
from textual.widgets import Input

from pult.app import PultApp
from pult.screens.cancel_lesson_screen import CancelLessonScreen
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


def test_palette_mapping_and_light_mode(palette):
    theme = theme_from_palette(palette)
    assert theme.primary == palette["accent"]
    assert theme.success == palette["green"]
    assert theme.warning == palette["yellow"]
    assert theme.error == palette["red"]
    assert theme.variables["block-cursor-background"] == palette["selection"]
    assert theme.dark
    assert not theme_from_palette(palette | {"mode": "light"}).dark
    del palette["mode"]
    assert not theme_from_palette(palette | {"background": "#ffffff"}).dark


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


@pytest.mark.parametrize("valid_at_start", [False, True])
def test_live_theme_keeps_modal_input_and_focus(
    tmp_path, monkeypatch, palette, valid_at_start
):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    path = tmp_path / "omarchy" / "colors.toml"
    if valid_at_start:
        write_palette(path, palette)

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            assert (
                app.theme.startswith("pult-omarchy-")
                if valid_at_start
                else app.theme == "gruvbox"
            )
            modal = CancelLessonScreen("5A")
            await app.push_screen(modal)
            await pilot.pause()
            field = modal.query_one(Input)
            field.value = "Noch nicht gespeichert"
            field.focus()
            field.cursor_position = 5
            cancel = modal.query_one("#abort-cancel-lesson")
            save = modal.query_one("#save-cancelled-lesson")
            assert cancel.styles.background == save.styles.background
            assert cancel.styles.background.a > 0
            save.focus()
            await pilot.pause()
            assert save.styles.background != cancel.styles.background
            field.focus()
            await pilot.pause()
            field.cursor_position = 5
            write_palette(path, palette | {"accent": "#88c0d0", "mode": "light"})
            # Tatsächlichen App-Timer prüfen, nicht nur die Refresh-Methode.
            await pilot.pause(1.2)
            assert app.current_theme.primary == "#88c0d0"
            assert (
                modal.query_one(".form-dialog").styles.border.top[1].hex.lower()
                == "#88c0d0"
            )
            assert not app.current_theme.dark
            assert app.screen is modal
            assert app.focused is field
            assert field.value == "Noch nicht gespeichert"
            assert field.cursor_position == 5
            current = app.theme
            path.write_text("broken = [")
            app.refresh_omarchy_theme()
            assert app.theme == current
            for accent in ["#abcdef", "#fedcba", "#123456"]:
                write_palette(path, palette | {"accent": accent})
                app.refresh_omarchy_theme()
                await pilot.pause()
                assert app.current_theme.primary == accent
                assert (
                    modal.query_one(".form-dialog").styles.border.top[1].hex.lower()
                    == accent
                )
            assert (
                len(
                    [
                        name
                        for name in app.available_themes
                        if name.startswith("pult-omarchy-")
                    ]
                )
                == 2
            )

    asyncio.run(run())
