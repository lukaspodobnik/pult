import json

from rich.cells import cell_len
from rich.text import Text
from textual.widgets.option_list import Option

from pult.school.school_class import SchoolClass, school_class_sort_key
from pult.school.subject import Subject
from pult.widgets.scrolling import OptionList


class ViewPicker(OptionList):
    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.border_title = "ANSICHTEN"
        self.class_subjects_by_option_id: dict[str, tuple[str, str]] = {}

    def refresh_options(
        self,
        school_classes: list[SchoolClass],
        subjects: list[Subject],
        highlighted_option_id: str | None = None,
        *,
        include_home: bool = True,
    ) -> None:
        """Ersetze die Navigation und erhalte nach Möglichkeit das Highlight."""
        subjects_by_id = {subject.id: subject for subject in subjects}
        class_width = max((cell_len(c.id) for c in school_classes), default=0)
        targets: dict[str, tuple[str, str]] = {}
        options = [Option("Übersicht", id="home")] if include_home else []
        for school_class in sorted(school_classes, key=school_class_sort_key):
            class_label = school_class.id + " " * (
                class_width - cell_len(school_class.id)
            )
            for subject_id in sorted(
                school_class.subject_ids,
                key=lambda value: (subjects_by_id[value].name.casefold(), value),
            ):
                # JSON erzeugt stabile, eindeutige IDs auch bei Sonderzeichen.
                # Die Auswahl wird über targets aufgelöst, nicht durch Textzerlegung.
                option_id = json.dumps([school_class.id, subject_id])
                targets[option_id] = (school_class.id, subject_id)
                options.append(
                    Option(
                        Text(
                            f"{class_label} · {subjects_by_id[subject_id].short_name}",
                            no_wrap=True,
                            overflow="ellipsis",
                        ),
                        id=option_id,
                    )
                )

        self.clear_options()
        self.class_subjects_by_option_id = targets
        # None zeichnet eine Trennlinie, ohne eine auswählbare Option anzulegen.
        self.add_options(
            [options[0], None, *options[1:]] if include_home and targets else options
        )

        option_ids = [option.id for option in options]
        self.highlighted = (
            option_ids.index(highlighted_option_id)
            if highlighted_option_id in option_ids
            else 0
        )


class TeachingPicker(OptionList):
    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(
            Option("Sequenzen", id="sequence-library"),
            Option("Protokoll", id="teaching-log"),
            id=id,
        )
        self.border_title = "UNTERRICHT"


class ManagementPicker(OptionList):
    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(
            Option("Klassen", id="edit-classes"),
            Option("Stundenplan", id="edit-timetable"),
            Option("Ausfälle", id="edit-closures"),
            None,
            Option("Einstellungen", id="settings"),
            id=id,
        )
        self.border_title = "VERWALTUNG"
        self._spacer_rows = 0

    def on_resize(self) -> None:
        self.call_after_refresh(self.align_settings)

    def align_settings(self) -> None:
        # Vier Einträge und eine Trennlinie; der freie Platz liegt vor der Linie.
        rows = max(0, self.content_size.height - 5)
        if rows == self._spacer_rows:
            return
        selected = (
            self.get_option_at_index(self.highlighted).id
            if self.highlighted is not None
            else None
        )
        self._spacer_rows = rows
        with self.prevent(OptionList.OptionHighlighted):
            self.clear_options()
            self.add_options(
                [
                    Option("Klassen", id="edit-classes"),
                    Option("Stundenplan", id="edit-timetable"),
                    Option("Ausfälle", id="edit-closures"),
                ]
            )
            if rows:
                self.add_option(Option(Text("\n" * (rows - 1)), disabled=True))
            self.add_options([None, Option("Einstellungen", id="settings")])
            if selected is not None:
                self.highlighted = self.get_option_index(selected)
