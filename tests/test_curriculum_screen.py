import asyncio

from test_ui_integration import prepare_root

from pult.app import PultApp
from pult.screens.curriculum_screen import (
    CurriculumScreen,
    CurriculumTree,
    curriculum_documents,
)
from pult.widgets.document_viewer import DocumentViewer


def test_personal_curriculum_overrides_defaults(tmp_path):
    directory = tmp_path / "curriculum/mathematik"
    directory.mkdir(parents=True)
    (directory / "jahrgang-05.md").write_text("# Persönlicher Lehrplan")
    documents = curriculum_documents(tmp_path, "mathematik")
    assert documents["jahrgang-05.md"] == "# Persönlicher Lehrplan"
    assert "kompetenzen.md" not in documents
    assert "jahrgang-13.md" in documents
    assert curriculum_documents(tmp_path, "unbekannt") == {}


def test_curriculum_flat_grade_tree_and_shared_viewer(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            screen = CurriculumScreen()
            await app.push_screen(screen)
            await pilot.pause()
            tree = screen.query_one(CurriculumTree)
            assert all(not node.is_expanded for node in tree.root.children)
            subject = next(
                n for n in tree.root.children if str(n.label) == "Mathematik"
            )
            assert [str(n.label) for n in subject.children] == [
                f"{i}. Jahrgangsstufe" for i in range(5, 14)
            ]
            assert all(not n.children and not n.allow_expand for n in subject.children)
            tree.move_cursor(subject)
            await pilot.pause()
            await pilot.press("space", "down")
            await pilot.pause()
            assert "Mathematik 5" in screen.query_one(DocumentViewer).source
            tree.move_cursor(subject.children[-1])
            await pilot.pause()
            assert "Mathematik 13" in screen.query_one(DocumentViewer).source
            assert screen.query_one("#curriculum-reader").scroll_y == 0

    asyncio.run(run())
