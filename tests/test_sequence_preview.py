from dataclasses import replace

from pult.widgets.sequence_preview import SequencePreview


def test_sequence_preview_structure_and_empty_state(sequences):
    sequence = sequences[0]
    sequence.lessons[0].material = ["Schere"]
    markdown = SequencePreview.render_sequence(sequence)
    assert sequence.title not in markdown
    assert markdown.count(". Stunde ·") == len(sequence.lessons)
    assert "1. Stunde · Zahlen ordnen" in markdown
    assert "Aufgaben\n• aufgabe-1" in markdown
    assert "Benötigtes Material\n• Schere" in markdown
    empty = SequencePreview.render_sequence(
        replace(sequence, lessons=[], recommended_lesson_count=None)
    )
    assert "Noch keine Unterrichtsstunden" in empty
    assert "---" not in empty


def test_selection_focus_reload_and_empty_state(sequences, tmp_path):
    import asyncio

    from textual.app import App
    from textual.widgets import Button

    from pult.curriculum.material import Lesson

    class PreviewApp(App):
        def compose(self):
            yield Button("Sequenzauswahl", id="left")
            yield SequencePreview(id="preview")

    async def run():
        app = PreviewApp()
        async with app.run_test(size=(110, 34)) as pilot:
            preview = app.query_one(SequencePreview)
            sequence = sequences[0]
            sequence.lessons.extend(
                Lesson(f"extra-{n}", f"Weitere Stunde {n}", goals=["Ziel"] * 3)
                for n in range(8)
            )
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
            await pilot.press("end")
            await pilot.pause()
            assert preview.selected_lesson.id == "extra-7"
            assert preview.scroll_y > 0
            selected = preview.selected_lesson.id
            position = preview.scroll_y
            preview.show_sequence(replace(sequence, title="Neuer Titel"))
            await pilot.pause()
            assert preview.selected_lesson.id == selected
            assert preview.scroll_y == position
            app.save_screenshot("sequence-preview.svg", path=tmp_path)
            preview.show_sequence(sequences[1])
            await pilot.pause()
            assert preview.selected_lesson.id == "lesson-3"
            assert preview.scroll_y == 0
            preview.show_sequence(
                replace(sequence, lessons=[], recommended_lesson_count=None)
            )
            await pilot.pause()
            await pilot.press("up", "down", "enter")
            assert preview.selected_lesson is None

    asyncio.run(run())
