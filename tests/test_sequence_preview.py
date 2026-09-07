from dataclasses import replace

from schooltools_tui.widgets.sequence_preview import SequencePreview


def test_sequence_preview_structure_and_empty_state(sequences):
    sequence = sequences[0]
    markdown = SequencePreview.render_sequence(sequence)
    assert sequence.title not in markdown
    assert markdown.count("\n---\n") == len(sequence.lessons) - 1
    assert "## 1. Stunde · Zahlen ordnen" in markdown
    assert "**Aufgaben**\n\n- Aufgabe 1" in markdown
    assert "**Notizen**\n\nHinweis" in markdown
    empty = SequencePreview.render_sequence(
        replace(sequence, lessons=[], recommended_lesson_count=None)
    )
    assert "Noch keine Unterrichtsstunden" in empty
    assert "---" not in empty
