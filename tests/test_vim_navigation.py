import asyncio

from textual.widgets import DataTable, Input, OptionList, Select, SelectionList, Tree

from schooltools_tui.app import SchooltoolsApp


def test_j_k_navigate_without_changing_text_input(monkeypatch):
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: None)
    class NavigationApp(SchooltoolsApp):
        CSS_PATH = []

        def show_initial_screen(self):
            pass

        def compose(self):
            yield OptionList("A", "B", id="options")
            yield SelectionList(("A", "a"), ("B", "b"), id="subjects")
            yield Select([("A", "a"), ("B", "b")], value="a", id="select")
            yield Input(id="input")
            tree = Tree("Root", id="tree")
            tree.root.add_leaf("A")
            tree.root.expand()
            yield tree
            yield DataTable(id="table")

    async def run():
        app = NavigationApp()
        async with app.run_test(size=(100, 60)) as pilot:
            for selector in ("#options", "#subjects"):
                options = app.query_one(selector, OptionList)
                options.focus()
                options.highlighted = 0
                await pilot.pause()
                assert app.focused is options
                await pilot.press("j")
                await pilot.pause()
                assert options.highlighted == 1
                await pilot.press("k")
                assert options.highlighted == 0
            field = app.query_one(Input)
            field.focus()
            await pilot.press("j", "k")
            assert field.value == "jk"
            tree = app.query_one(Tree)
            tree.focus()
            tree.move_cursor(tree.root)
            await pilot.press("j")
            assert tree.cursor_node is tree.root.children[0]
            await pilot.press("k")
            assert tree.cursor_node is tree.root
            table = app.query_one(DataTable)
            table.add_column("Test")
            table.add_rows([("A",), ("B",)])
            table.focus()
            await pilot.press("j")
            assert table.cursor_row == 1
            await pilot.press("k")
            assert table.cursor_row == 0
            select = app.query_one(Select)
            select.focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("j")
            await pilot.pause()
            await pilot.press("enter")
            assert select.value == "b"

    asyncio.run(run())
