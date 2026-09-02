from textual.widgets import OptionList
from textual.widgets.option_list import Option

from schooltools_tui.school_class import SchoolClass


class ViewPicker(OptionList):
    def refresh_options(self, school_classes: list[SchoolClass]) -> None:
        self.clear_options()

        self.add_option(Option("Home", id="home"))
        for school_class in school_classes:
            self.add_option(Option(school_class.id, id=f"class-{school_class.id}"))

        self.highlighted = 0
        self.focus()


class ManagementPicker(OptionList):
    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(
            Option("Klasse anlegen", id="create-class"),
            Option("Sequenzbibliothek", id="sequence-library"),
            Option("Stundenplan", id="edit-timetable"),
            id=id,
        )
