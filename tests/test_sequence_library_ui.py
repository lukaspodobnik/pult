import asyncio
from contextlib import nullcontext
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from test_ui_integration import prepare_root

from schooltools_tui.app import SchooltoolsApp
from schooltools_tui.curriculum.sequence import get_sequence_path, save_sequence
from schooltools_tui.screens.main_screen import MainScreen
from schooltools_tui.screens.sequence_library_screen import SequenceLibraryScreen
from schooltools_tui.storage import save_toml
from schooltools_tui.widgets.navigation import ManagementPicker
from schooltools_tui.widgets.sequence_preview import SequencePreview
from schooltools_tui.widgets.sequence_tree import SequenceTree


@pytest.mark.parametrize("editor_result", ["saved", "invalid", "missing"])
def test_library_navigation_and_editor_return(tmp_path, monkeypatch, editor_result):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)

    async def run():
        app = SchooltoolsApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            picker = app.screen.query_one(ManagementPicker)
            picker.focus()
            picker.highlighted = 1
            await pilot.press("enter")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SequenceLibraryScreen)
            tree = screen.query_one(SequenceTree)
            assert not tree.show_root
            assert all(not node.is_expanded for node in tree.root.children)

            def leaves(node):
                if node.data is not None:
                    yield node
                for child in node.children:
                    yield from leaves(child)

            nodes = list(leaves(tree.root))
            assert len(nodes) == 116
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
                if editor_result == "missing":
                    raise FileNotFoundError("Editor fehlt")
                if editor_result == "invalid":
                    save_toml(path, {})
                else:
                    save_sequence(config.root, updated)
                return SimpleNamespace(returncode=0)

            # Nur den Editoraufruf ersetzen, nicht das globale subprocess-Modul.
            monkeypatch.setattr(
                "schooltools_tui.screens.sequence_library_screen.subprocess",
                SimpleNamespace(run=editor),
            )
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen is screen
            if editor_result == "saved":
                assert node.data == updated
                assert node.label.plain == updated.title
                notifications.assert_not_called()
                headings = screen.query_one(SequencePreview).document.query(
                    "MarkdownH1"
                )
                assert any(
                    updated.title in heading.render().plain for heading in headings
                )
            else:
                assert node.data == original
                assert notifications.call_args.kwargs["severity"] == "error"
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
