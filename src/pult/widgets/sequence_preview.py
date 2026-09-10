from rich.text import Text
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from pult.curriculum.sequence import Lesson, Sequence
from pult.presentation import UNTITLED_LESSON


class SequencePreview(OptionList):
    """Sequenzüberblick mit einem auswählbaren Eintrag je vollständiger Stunde."""

    def __init__(self, *, id: str | None) -> None:
        super().__init__(Option("Wähle eine Sequenz.", disabled=True), id=id)
        self.border_title = "VORSCHAU"
        self.sequence: Sequence | None = None

    @property
    def selected_lesson(self) -> Lesson | None:
        if self.sequence is None or self.highlighted is None:
            return None
        index = self.highlighted - 1  # Der erste Eintrag ist die Metadatenzeile.
        if 0 <= index < len(self.sequence.lessons):
            return self.sequence.lessons[index]
        return None

    def show_sequence(self, sequence: Sequence) -> None:
        """Lade den Überblick; Aktualisierungen erhalten die Auswahl anhand der ID."""
        same_sequence = self.sequence is not None and (
            self.sequence.grade_level,
            self.sequence.subject_id,
            self.sequence.id,
        ) == (sequence.grade_level, sequence.subject_id, sequence.id)
        selected = self.selected_lesson
        selected_id = selected.id if same_sequence and selected else None
        position = self.scroll_y if same_sequence else 0
        self.sequence = sequence
        self.clear_options()
        self.add_option(Option(self.metadata(sequence) + "\n", disabled=True))
        for index, lesson in enumerate(sequence.lessons, start=1):
            if index > 1:
                self.add_option(None)
            self.add_option(Option(self.render_lesson(lesson, index), id=lesson.id))
        if not sequence.lessons:
            self.add_option(
                Option("Noch keine Unterrichtsstunden eingetragen.", disabled=True)
            )
        self.border_title = sequence.title
        self.highlighted = next(
            (
                index
                for index, lesson in enumerate(sequence.lessons, start=1)
                if lesson.id == selected_id
            ),
            1 if sequence.lessons else None,
        )
        self.call_after_refresh(self.scroll_to, y=position, animate=False)

    @staticmethod
    def metadata(sequence: Sequence) -> str:
        text = f"Lehrplanabschnitt {sequence.curriculum_section_id}"
        if sequence.recommended_lesson_count is not None:
            count = sequence.recommended_lesson_count
            text += f" · Richtwert: {count} {'Stunde' if count == 1 else 'Stunden'}"
        return text

    @staticmethod
    def render_lesson(lesson: Lesson, index: int) -> Text:
        text = Text(f"{index}. Stunde · {lesson.title or UNTITLED_LESSON}\n", style="")
        text.stylize("bold", 0, len(text))
        for label, values in [
            ("Aufgaben", [task.id for task in lesson.tasks]),
            ("Ziele", lesson.goals),
            ("Benötigtes Material", lesson.material),
        ]:
            if values:
                text.append(f"\n{label}\n", style="bold")
                text.append("\n".join(f"• {value}" for value in values) + "\n")
            elif label == "Aufgaben":
                text.append("\nNoch keine Aufgaben eingetragen.\n", style="italic")
        if lesson.phases:
            text.append("\nVerlauf\n", style="bold")
            for phase in lesson.phases:
                text.append(f"• {phase.title}: ", style="bold")
                text.append(phase.text + "\n")
        return text

    @classmethod
    def render_sequence(cls, sequence: Sequence) -> str:
        """Textfassung desselben Überblicks, ohne zusätzliche gepflegte Inhalte."""
        return "\n\n".join(
            [cls.metadata(sequence)]
            + [
                cls.render_lesson(lesson, index).plain
                for index, lesson in enumerate(sequence.lessons, start=1)
            ]
            + (
                []
                if sequence.lessons
                else ["Noch keine Unterrichtsstunden eingetragen."]
            )
        )
