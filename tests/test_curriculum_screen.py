import asyncio

from test_ui_integration import prepare_root
from textual.widgets import MarkdownViewer

from pult.app import PultApp
from pult.screens.curriculum_screen import (
    CurriculumScreen,
    CurriculumTree,
    curriculum_documents,
)
from pult.screens.main_screen import MainScreen
from pult.widgets.navigation import TeachingPicker


def test_personal_curriculum_overrides_defaults(tmp_path):
    directory = tmp_path / "curriculum" / "mathematik"
    directory.mkdir(parents=True)
    (directory / "jahrgang-05.md").write_text("# Persönlicher Lehrplan")
    documents = curriculum_documents(tmp_path, "mathematik")
    assert documents["jahrgang-05.md"] == "# Persönlicher Lehrplan"
    assert "kompetenzen.md" in documents
    assert "jahrgang-13.md" in documents
    assert curriculum_documents(tmp_path, "unbekannt") == {}


def test_curriculum_highlight_navigation(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            picker = app.screen.query_one(TeachingPicker)
            picker.focus()
            picker.highlighted = picker.get_option_index("curriculum")
            await pilot.press("enter")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CurriculumScreen)
            tree = screen.query_one(CurriculumTree)
            reader = screen.query_one(MarkdownViewer)
            assert tree.guide_depth == 2
            assert not tree.show_root
            assert screen.query_one("#curriculum-navigation").region.width == 36
            subject = next(
                node for node in tree.root.children if str(node.label) == "Mathematik"
            )
            assert [str(node.label) for node in subject.children] == [
                "Lehrpläne",
                "Leitideen",
                "Kompetenzen",
                "Anforderungsbereiche",
                "Operatoren",
            ]
            assert tree.border_title == "LEHRPLAN"
            assert tree.region.y == reader.region.y == 1
            assert set(screen.focus_chain) == {tree}
            await pilot.press("tab", "shift+tab")
            assert app.focused is tree
            subject.expand()
            await pilot.pause()
            grade = subject.children[0].children[0]
            tree.move_cursor(grade)
            await pilot.pause()
            assert "Mathematik 5" in (screen.current_source or "")
            grade.expand()
            await pilot.pause()
            section = grade.children[1]
            tree.move_cursor(section)
            await pilot.pause()
            assert reader.border_title == section.data.title
            tree.move_cursor(tree.root.children[0])
            await pilot.pause()
            assert reader.border_title == section.data.title
            competence = subject.children[2]
            tree.move_cursor(competence)
            await pilot.pause()
            assert "Mathematisch argumentieren" in (screen.current_source or "")
            assert reader.show_vertical_scrollbar
            assert reader.vertical_scrollbar.region.right == reader.region.right - 1
            await pilot.click("#curriculum-reader", offset=(10, 10))
            assert app.focused is tree
            await pilot.press("tab", "shift+tab")
            assert app.focused is tree
            old_border = tree.styles.border
            tree.blur()
            await pilot.pause()
            assert tree.styles.border == old_border
            tree.focus()
            subject = next(
                node
                for node in tree.root.children
                if str(node.label) == "Informatik NTG"
            )
            subject.expand()
            await pilot.pause()
            grade = subject.children[0].children[0]
            tree.move_cursor(grade)
            await pilot.pause()
            assert "Informatik" in (screen.current_source or "")
            assert "Mathematisch argumentieren" not in (screen.current_source or "")
            await pilot.press("escape")
            assert isinstance(app.screen, MainScreen)

    asyncio.run(run())
