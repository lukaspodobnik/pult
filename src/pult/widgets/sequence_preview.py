from textual.widgets import MarkdownViewer

from pult.curriculum.sequence import Sequence
from pult.presentation import UNTITLED_LESSON


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
        metadata = f"Lehrplanabschnitt {sequence.curriculum_section_id}"
        if sequence.recommended_lesson_count is not None:
            count = sequence.recommended_lesson_count
            metadata += f" · Richtwert: {count} {'Stunde' if count == 1 else 'Stunden'}"
        lines = [metadata, ""]

        for index, lesson in enumerate(sequence.lessons, start=1):
            if index > 1:
                lines.extend(["", "---", ""])
            title = lesson.title or UNTITLED_LESSON
            lines.extend(
                [
                    "",
                    f"## {index}. Stunde · {title}",
                    "",
                ]
            )

            if lesson.tasks:
                lines.extend(["**Aufgaben**", ""])
                lines.extend(f"- {task.id}" for task in lesson.tasks)
            else:
                lines.append("*Noch keine Aufgaben eingetragen.*")

            if lesson.goals:
                lines.extend(["", "**Ziele**", ""])
                lines.extend(f"- {goal}" for goal in lesson.goals)
            if lesson.material:
                lines.extend(["", "**Benötigtes Material**", ""])
                lines.extend(f"- {item}" for item in lesson.material)
            if lesson.phases:
                lines.extend(["", "**Verlauf**", ""])
                lines.extend(
                    f"- **{phase.title}:** {phase.text}" for phase in lesson.phases
                )

        if not sequence.lessons:
            lines.extend(
                [
                    "",
                    "*Noch keine Unterrichtsstunden eingetragen.*",
                ]
            )

        return "\n".join(lines)
