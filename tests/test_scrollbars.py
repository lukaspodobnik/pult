import asyncio

from textual.app import App

from pult.widgets.scrolling import Tree


def test_scrollbars_follow_frame_edges_without_moving_content(tmp_path):
    class ScrollApp(App):
        CSS = """
        Tree { width: 30; height: 10; border: round white; padding: 1 2;
               scrollbar-size: 1 1; }
        """

        def compose(self):
            tree = Tree("Root")
            for index in range(20):
                tree.root.add_leaf(f"{index}: " + "Langer Sequenzname " * 8)
            tree.root.expand()
            yield tree

    async def run():
        app = ScrollApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            tree = app.query_one(Tree)
            assert tree.show_vertical_scrollbar
            assert tree.horizontal_scrollbar.region.height == 1
            assert tree.show_horizontal_scrollbar
            assert tree.vertical_scrollbar.region.right == tree.region.right - 1
            assert tree.horizontal_scrollbar.region.bottom == tree.region.bottom - 1
            assert tree.styles.padding.right == 2
            app.save_screenshot("scrollbars.svg", path=str(tmp_path))

    asyncio.run(run())
