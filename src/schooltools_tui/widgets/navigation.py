import json

from textual.widgets import OptionList
from textual.widgets.option_list import Option

from schooltools_tui.school.school_class import SchoolClass, school_class_sort_key
from schooltools_tui.school.subject import Subject


class ViewPicker(OptionList):
    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.class_subjects_by_option_id: dict[str, tuple[str, str]] = {}

    def refresh_options(
        self,
        school_classes: list[SchoolClass],
        subjects: list[Subject],
        highlighted_option_id: str | None = None,
    ) -> None:
        """Ersetze die Navigation und erhalte nach Möglichkeit das Highlight."""
        subjects_by_id = {subject.id: subject for subject in subjects}
        targets: dict[str, tuple[str, str]] = {}
        options = [Option("Home", id="home")]
        for school_class in sorted(school_classes, key=school_class_sort_key):
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
                        f"{school_class.id} · {subjects_by_id[subject_id].short_name}",
                        id=option_id,
                    )
                )

        self.clear_options()
        self.class_subjects_by_option_id = targets
        self.add_options(options)

        option_ids = [option.id for option in options]
        self.highlighted = (
            option_ids.index(highlighted_option_id)
            if highlighted_option_id in option_ids
            else 0
        )


class ManagementPicker(OptionList):
    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(
            Option("Klassen", id="edit-classes"),
            Option("Sequenzbibliothek", id="sequence-library"),
            Option("Stundenplan", id="edit-timetable"),
            Option("Ausfälle", id="edit-closures"),
            Option("Unterrichtsprotokoll", id="teaching-log"),
            id=id,
        )
