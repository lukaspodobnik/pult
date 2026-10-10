import asyncio
from pathlib import Path
from unittest.mock import Mock

from textual.app import App

from pult.widgets.materials import MaterialsPane


def test_named_material_links_open_correct_targets(tmp_path, monkeypatch):
    folder = tmp_path / "stunden/test"
    folder.mkdir(parents=True)
    files = tmp_path / "dateien"
    files.mkdir()
    presentation = files / "präsentation.key"
    presentation.write_text("Testdatei")
    opened = Mock()
    monkeypatch.setattr("pult.widgets.materials.subprocess.Popen", opened)

    class MaterialsApp(App):
        def compose(self):
            yield MaterialsPane(
                "- Schere\n- [Keynote](../../dateien/pr%C3%A4sentation.key)\n- [Webseite](https://example.org/unterricht)",
                folder / "material.md",
                tmp_path,
            )

    async def run():
        app = MaterialsApp()
        browser = Mock()
        monkeypatch.setattr(app, "open_url", browser)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.click("#material-1")
            assert Path(opened.call_args.args[0][-1]) == presentation
            await pilot.click("#material-2")
            browser.assert_called_once_with("https://example.org/unterricht")

    asyncio.run(run())
