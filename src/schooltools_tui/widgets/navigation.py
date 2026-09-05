from textual.widgets import OptionList
from textual.widgets.option_list import Option

from schooltools_tui.school.school_class import SchoolClass


class ViewPicker(OptionList):
    def refresh_options(
        self,
        school_classes: list[SchoolClass],
        highlighted_option_id: str | None = None,
    ) -> None:
        """Ersetze die Navigation und erhalte nach Möglichkeit das Highlight."""
        self.clear_options()

        options = [Option("Home", id="home")]
        for school_class in school_classes:
            options.append(
                Option(school_class.id, id=f"class-{school_class.id}")
            )

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
