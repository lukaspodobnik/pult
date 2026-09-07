from textual.widgets import MarkdownViewer

from schooltools_tui.curriculum.sequence import Sequence
from schooltools_tui.presentation import UNTITLED_LESSON


class SequencePreview(MarkdownViewer):
    can_focus = True
    can_focus_children = False

    def __init__(self, *, id: str | None) -> None:
        super().__init__("Wähle eine Sequenz.", show_table_of_contents=False, id=id)
        self.border_title = "VORSCHAU"

    def show_sequence(self, sequence: Sequence) -> None:
        """Ersetze die Vorschau durch die formatierte Darstellung einer Sequenz."""
        self.document.update(self.render_sequence(sequence))
        self.border_title = sequence.title
        self.scroll_home(animate=False)

    @staticmethod
    def render_sequence(sequence: Sequence) -> str:
        """Formatiere eine Sequenz als Markdown für die Vorschau."""
        lines = [
            f"# {sequence.title}",
            "",
            f"**Lehrplanabschnitt:** {sequence.curriculum_section_id}",
            "",
        ]

        if sequence.recommended_lesson_count is not None:
            lines.append(
                f"**Empfohlener Umfang:** {sequence.recommended_lesson_count} Stunden"
            )

        lines.extend(["", "## Unterrichtsstunden"])

        for index, lesson in enumerate(sequence.lessons, start=1):
            title = lesson.title or UNTITLED_LESSON
            lines.extend(
                [
                    "",
                    f"### {index}. {title}",
                    "",
                ]
            )

            if lesson.tasks:
                lines.append("**Aufgaben:**")
                lines.extend(f"- {task}" for task in lesson.tasks)
            else:
                lines.append("*Noch keine Aufgaben eingetragen.*")

            if lesson.notes:
                lines.extend(
                    [
                        "",
                        "**Notizen:**",
                        "",
                        lesson.notes,
                    ]
                )

        if not sequence.lessons:
            lines.extend(
                [
                    "",
                    "*Noch keine Unterrichtsstunden eingetragen.*",
                ]
            )

        return "\n".join(lines)
