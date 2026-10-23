from dataclasses import replace

from pult.widgets.sequence_preview import SequencePreview


def test_selection_survives_reload_and_resets_for_another_sequence(sequences, tmp_path):
    import asyncio

    from textual.app import App
    from textual.widgets import Button

    class PreviewApp(App):
        def compose(self):
            yield Button("Sequenzauswahl", id="left")
            yield SequencePreview(id="preview")

    async def run():
        app = PreviewApp()
        async with app.run_test(size=(110, 34)) as pilot:
            preview = app.query_one(SequencePreview)
            sequence = sequences[0]
            preview.show_sequence(sequence)
            await pilot.pause()
            assert app.focused is not preview
            assert preview.selected_lesson.id == "lesson-1"
            await pilot.press("tab", "down")
            assert app.focused is preview
            assert preview.selected_lesson.id == "lesson-2"
            screen = app.screen
            await pilot.press("enter")
            assert app.screen is screen
            assert preview.selected_lesson.id == "lesson-2"
            selected = preview.selected_lesson.id
            preview.show_sequence(replace(sequence, title="Neuer Titel"))
            await pilot.pause()
            assert preview.selected_lesson.id == selected
            preview.show_sequence(sequences[1])
            await pilot.pause()
            assert preview.selected_lesson.id == "lesson-3"
            preview.show_sequence(
                replace(sequence, lessons=[], recommended_lesson_count=None)
            )
            await pilot.pause()
            await pilot.press("up", "down", "enter")
            assert preview.selected_lesson is None

    asyncio.run(run())
