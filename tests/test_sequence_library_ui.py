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
    load_sequence_library,
    save_sequence,
)
from pult.screens.main_screen import MainScreen
from pult.screens.sequence_library_screen import SequenceLibraryScreen
from pult.storage import save_toml
from pult.widgets.navigation import ManagementPicker
from pult.widgets.sequence_preview import SequencePreview
from pult.widgets.sequence_tree import SequenceTree


@pytest.mark.parametrize("editor_result", ["saved", "invalid", "missing"])
def test_library_navigation_and_editor_return(tmp_path, monkeypatch, editor_result):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    library_loader = Mock(wraps=load_sequence_library)
    monkeypatch.setattr(
        "pult.services.sequence_library.load_sequence_library",
        library_loader,
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            picker = app.screen.query_one(ManagementPicker)
            picker.focus()
            picker.highlighted = picker.get_option_index("sequence-library")
            await pilot.press("enter")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SequenceLibraryScreen)
            tree = screen.query_one(SequenceTree)
            preview = screen.query_one(SequencePreview)
            assert not screen.query("Header")
            assert tree.guide_depth == 2
            assert tree.border_title == "SEQUENZBIBLIOTHEK"
            assert (tree.region.y, tree.region.bottom) == (
                preview.region.y,
                preview.region.bottom,
            )
            assert set(screen.focus_chain) == {tree, preview}
            tree.focus()
            await pilot.pause()
            assert tree.styles.background_tint.a == 0
            assert tree.styles.border.top[1] != preview.styles.border.top[1]
            await pilot.press("tab")
            assert app.focused is preview
            await pilot.pause()
            assert preview.styles.background_tint.a == 0
            assert preview.styles.border.top[1] != tree.styles.border.top[1]
            await pilot.press("tab")
            assert app.focused is tree
            assert not tree.show_root
            assert app.focused is tree
            assert tree.cursor_node is tree.root.children[0]
            assert all(not node.is_expanded for node in tree.root.children)

            def leaves(node):
                if node.data is not None:
                    yield node
                for child in node.children:
                    yield from leaves(child)

            nodes = list(leaves(tree.root))
            assert len(nodes) == 116
            assert all(not node.allow_expand for node in nodes)
            # Home und Bibliotheksbaum teilen denselben ersten Ladevorgang.
            library_loader.assert_called_once_with(config.root)
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
                "pult.screens.sequence_library_screen.subprocess",
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
                assert library_loader.call_count == 2
                assert node.data == updated
                assert node.label.plain == updated.title
                notifications.assert_not_called()
                preview = screen.query_one(SequencePreview)
                assert preview.border_title == updated.title
                assert not preview.document.query("MarkdownH1")
            else:
                assert node.data == original
                assert notifications.call_args.kwargs["severity"] == "error"
                if editor_result == "invalid":
                    with pytest.raises(SequenceFileError):
                        _ = screen.sequence_library
                else:
                    assert original in screen.sequence_library
                    assert library_loader.call_count == 1
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
