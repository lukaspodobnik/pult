import asyncio
from contextlib import nullcontext
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from test_ui_integration import prepare_root

from pult.app import PultApp
from pult.curriculum.sequence import (
    SequenceFileError,
    get_sequence_path,
    save_sequence,
)
from pult.screens.main_screen import MainScreen
from pult.screens.teaching.sequence_library_screen import SequenceLibraryScreen
from pult.storage import save_toml
from pult.widgets.navigation import TeachingPicker
from pult.widgets.sequence_preview import SequencePreview
from pult.widgets.sequence_tree import SequenceTree


@pytest.mark.parametrize("editor_result", ["saved", "invalid"])
def test_library_navigation_and_editor_return(tmp_path, monkeypatch, editor_result):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            picker = app.screen.query_one(TeachingPicker)
            picker.focus()
            picker.highlighted = picker.get_option_index("sequence-library")
            await pilot.press("enter")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SequenceLibraryScreen)
            tree = screen.query_one(SequenceTree)
            preview = screen.query_one(SequencePreview)
            tree.focus()
            await pilot.press("tab")
            assert app.focused is preview
            await pilot.press("tab")
            assert app.focused is tree

            def leaves(node):
                if node.data is not None:
                    yield node
                for child in node.children:
                    yield from leaves(child)

            nodes = list(leaves(tree.root))
            assert len(nodes) == len(screen.sequence_library)
            node = nodes[0]
            original = node.data
            updated = replace(original, title="Geänderter Sequenzplan")
            node_parent = node.parent
            while node_parent is not None:
                node_parent.expand()
                node_parent = node_parent.parent
            await pilot.pause()
            tree.move_cursor(node)
            tree.focus()
            await pilot.pause()
            notifications = Mock()
            monkeypatch.setattr(screen, "notify", notifications)
            monkeypatch.setattr(app, "suspend", nullcontext)

            def editor(command, *, check):
                path = get_sequence_path(
                    config.root, original.grade_level, original.subject_id, original.id
                )
                assert command == ["true", str(path)]
                if editor_result == "invalid":
                    save_toml(path, {})
                else:
                    save_sequence(config.root, updated)
                return SimpleNamespace(returncode=0)

            # Nur den Editoraufruf ersetzen, nicht das globale subprocess-Modul.
            monkeypatch.setattr(
                "pult.screens.teaching.sequence_library_screen.subprocess",
                SimpleNamespace(run=editor),
            )
            await pilot.press("enter")
            await pilot.pause()
            assert node.data == original
            notifications.assert_not_called()
            await pilot.press("e")
            await pilot.pause()
            assert app.screen is screen
            if editor_result == "saved":
                assert updated in screen.sequence_library
                assert node.data == updated
                notifications.assert_not_called()
                preview = screen.query_one(SequencePreview)
                assert preview.border_title == updated.title
                assert preview.sequence.title == updated.title
            else:
                assert node.data == original
                assert notifications.call_args.kwargs["severity"] == "error"
                with pytest.raises(SequenceFileError):
                    _ = screen.sequence_library
            # Erst nach dem Rendern schließen; keine Markdown-Tasks beim Shutdown abbrechen.
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, MainScreen)

    # Markdown verwendet einen Threadpool. Dessen Beenden läuft hier explizit
    # mit Timeout: asyncio.run hängt in dieser Testumgebung sonst beim Shutdown.
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(run())
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(
                asyncio.wait_for(loop.shutdown_default_executor(), timeout=2)
            )
        finally:
            loop.close()
