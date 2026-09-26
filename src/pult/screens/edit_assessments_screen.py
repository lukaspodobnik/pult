from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.widgets import Static
from textual.widgets.option_list import Option

from pult.presentation import format_date
from pult.school.assessment_requirements import load_assessment_requirements
from pult.school.calendar import Closure
from pult.school.school_class import load_school_classes
from pult.school.subject import load_subjects
from pult.screens.base_screen import PultScreen
from pult.screens.confirmation_screen import ConfirmationScreen
from pult.screens.edit_assessment_screen import EditAssessmentScreen
from pult.services.assessment_conflicts import assessment_conflicts
from pult.services.assessment_planning import get_assessment_planning_gaps
from pult.services.assessments import (
    ScopedAssessment,
    assessment_kind_issue,
    complete_assessment,
    delete_assessment,
    list_assessments,
    reopen_assessment,
)
from pult.widgets.button import Button
from pult.widgets.footer import PultFooter
from pult.widgets.scrolling import Horizontal, OptionList, Vertical, VerticalScroll


class EditAssessmentsScreen(PultScreen[None]):
    BINDINGS: ClassVar = [
        ("a", "create", "Anlegen"),
        ("n", "complete", "Abschließen"),
        ("p", "reopen", "Rückgängig"),
        ("e", "edit", "Bearbeiten"),
        ("d", "delete", "Löschen"),
        ("escape", "cancel", "Zurück"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[ScopedAssessment] = []
        self.selected_key: tuple[str, str] | None = None
        self.subjects: dict[str, str] = {}
        self.kind_issues: dict[tuple[str, str], str | None] = {}
        self.conflicts: dict[tuple[str, str], tuple[Closure, ...]] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="assessments-screen"):
            with Vertical(id="assessments-frame") as frame:
                frame.border_title = "LEISTUNGSNACHWEISE"
                yield Static(id="assessments-headings")
                yield Static(
                    "Noch keine Leistungsnachweise geplant.", id="assessments-empty"
                )
                yield OptionList(id="assessments-list")
            with Horizontal(id="assessment-summary"):
                with VerticalScroll(
                    id="assessment-details", can_focus=False
                ) as details:
                    details.border_title = "TERMINDETAILS"
                    yield Static(id="assessment-details-text", markup=False)
                with Vertical(id="assessment-planning") as planning:
                    planning.border_title = "NOCH ZU PLANEN"
                    yield Static(id="assessment-planning-headings")
                    with VerticalScroll(id="assessment-planning-rows", can_focus=False):
                        yield Static(id="assessment-planning-text", markup=False)
            with Horizontal(classes="management-actions"):
                yield Button("Anlegen", id="create-assessment")
                yield Button("Bearbeiten", id="edit-assessment", disabled=True)
                yield Button(
                    "Löschen", id="delete-assessment", variant="error", disabled=True
                )
                yield Button("Abschließen", id="complete-assessment", disabled=True)
                yield Button("Rückgängig", id="reopen-assessment", disabled=True)
                yield Static(classes="action-spacer")
                yield Button("Zurück", id="close-assessments")
        yield PultFooter()

    def on_mount(self) -> None:
        self.reload_entries()

    def reload_entries(self) -> None:
        try:
            self.entries = list_assessments(self.app_config)
            self.kind_issues = {
                (item.school_class_id, item.assessment.id): assessment_kind_issue(
                    self.app_config, item.school_class_id, item.assessment
                )
                for item in self.entries
            }
            self.conflicts = {
                (item.school_class_id, item.assessment.id): assessment_conflicts(
                    self.app_config, item.school_class_id, item.assessment
                )
                for item in self.entries
            }
            self.subjects = {
                item.id: item.name for item in load_subjects(self.app_config.root)
            }
        except (OSError, ValueError) as error:
            self.notify(str(error), severity="error")
            return
        try:
            self.update_planning()
        except (OSError, ValueError) as error:
            self.query_one("#assessment-planning-text", Static).update(
                f"Planung konnte nicht geprüft werden: {error}"
            )
        keys = [(item.school_class_id, item.assessment.id) for item in self.entries]
        if self.selected_key not in keys:
            self.selected_key = keys[0] if keys else None
        listing = self.query_one("#assessments-list", OptionList)
        listing.clear_options()
        listing.add_options(
            Option(self.row(item), id=str(index))
            for index, item in enumerate(self.entries)
        )
        listing.highlighted = (
            keys.index(self.selected_key) if self.selected_key else None
        )
        self.query_one("#assessments-empty").display = not self.entries
        self.query_one("#assessments-headings", Static).update(
            self.columns(("Datum", "Klasse", "Fach", "Nr. / Art", "Bezeichnung"))
        )
        for name in ("edit", "delete"):
            self.query_one(f"#{name}-assessment", Button).disabled = not self.entries
        self.update_details()
        listing.focus()

    def update_planning(self) -> None:
        classes = load_school_classes(
            self.app_config.root, self.app_config.active_school_year
        )
        requirements = load_assessment_requirements(
            self.app_config.root, self.app_config.active_school_year
        )
        gaps = get_assessment_planning_gaps(
            classes,
            requirements,
            self.entries,
            {key for key, conflicts in self.conflicts.items() if conflicts},
        )
        headings = self.query_one("#assessment-planning-headings", Static)
        headings.display = bool(gaps)
        headings.update(self.planning_columns(("Klasse", "Fach", "Groß", "Klein")))
        text = Text()
        for index, gap in enumerate(gaps):
            if index:
                text.append("\n")
            text.append_text(
                self.planning_columns(
                    (
                        gap.school_class_id,
                        self.subjects.get(gap.subject_id, gap.subject_id),
                        str(gap.large) if gap.large else "—",
                        str(gap.small) if gap.small else "—",
                    )
                )
            )
        if not gaps:
            text.append(
                "Alle Mindestzahlen sind durch geplante oder durchgeführte LNWs abgedeckt."
                if classes
                else "Noch keine Klassen angelegt."
            )
        self.query_one("#assessment-planning-text", Static).update(text)

    def planning_columns(self, values: tuple[str, str, str, str]) -> Text:
        width = max(30, self.query_one("#assessment-planning-rows").content_size.width)
        widths = (8, max(10, width - 22), 7, 7)
        text = Text(no_wrap=True, overflow="ellipsis")
        for index, (value, size) in enumerate(zip(values, widths)):
            part = Text(value)
            part.truncate(size - 1, overflow="ellipsis")
            part.align("center" if index >= 2 else "left", size)
            text.append_text(part)
        return text

    def columns(self, values: tuple[str, ...]) -> Text:
        width = max(92, self.query_one("#assessments-list").content_size.width)
        widths = (12, 7, 32, 14, max(19, width - 73))
        result = Text(no_wrap=True, overflow="ellipsis")
        for index, (value, size) in enumerate(zip(values, widths)):
            part = Text(value)
            part.truncate(size, overflow="ellipsis")
            part.align("left", size)
            if index:
                result.append("  ")
            result.append_text(part)
        return result

    def row(self, item: ScopedAssessment) -> Text:
        entry = item.assessment
        key = (item.school_class_id, entry.id)
        marker = "⚠ " if self.kind_issues.get(key) or self.conflicts.get(key) else ""
        if entry.completed_on:
            marker += "✓ "
        return self.columns(
            (
                format_date(entry.date),
                item.school_class_id,
                self.subjects.get(entry.subject_id, entry.subject_id),
                f"{marker}{item.number}. {entry.kind.abbreviation}",
                entry.title,
            )
        )

    def selected(self) -> ScopedAssessment | None:
        return next(
            (
                item
                for item in self.entries
                if (item.school_class_id, item.assessment.id) == self.selected_key
            ),
            None,
        )

    def update_details(self) -> None:
        item = self.selected()
        completed = item is not None and item.assessment.completed_on is not None
        for action in ("edit", "delete", "complete"):
            self.query_one(f"#{action}-assessment", Button).disabled = (
                item is None or completed
            )
        self.query_one("#reopen-assessment", Button).disabled = not completed
        text = "Noch keine Leistungsnachweise geplant."
        if item:
            entry = item.assessment
            linked = [
                other.assessment
                for other in self.entries
                if other.school_class_id == item.school_class_id
                and other.assessment.subject_id == entry.subject_id
                and other.assessment.id != entry.id
                and entry.group_id
                and other.assessment.group_id == entry.group_id
            ]
            text = f"{item.number}. {entry.kind.label} · {entry.title}\n"
            text += f"{item.school_class_id} · {self.subjects.get(entry.subject_id, entry.subject_id)}\n\n"
            text += f"{format_date(entry.date, with_weekday=True)} · {entry.start:%H:%M} Uhr · {entry.duration_minutes} Minuten\n"
            text += "Belegte Unterrichtsstunden: " + (
                ", ".join(map(str, entry.occupied_periods))
                if entry.occupied_periods
                else "keine (außerhalb des eigenen Unterrichts)"
            )
            text += "\nVerknüpft: " + (
                "; ".join(
                    f"{format_date(other.date)} · {other.title}" for other in linked
                )
                or "—"
            )
            if entry.completed_on is not None:
                text += f"\nDurchgeführt am {format_date(entry.completed_on)}"
            if issue := self.kind_issues.get((item.school_class_id, entry.id)):
                text += f"\n⚠ {issue}"
            for closure in self.conflicts.get((item.school_class_id, entry.id), ()):
                text += f"\n⚠ Terminkonflikt: {closure.name} ({format_date(closure.start)} – {format_date(closure.end)})"
        self.query_one("#assessment-details-text", Static).update(text)

    @on(OptionList.OptionHighlighted, "#assessments-list")
    def highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_id is not None and int(event.option_id) < len(self.entries):
            item = self.entries[int(event.option_id)]
            self.selected_key = item.school_class_id, item.assessment.id
            self.update_details()

    @on(OptionList.OptionSelected, "#assessments-list")
    def open_selected(self) -> None:
        self.action_edit()

    def on_resize(self) -> None:
        if self.is_mounted:
            self.call_after_refresh(self.refresh_columns)

    def refresh_columns(self) -> None:
        try:
            self.update_planning()
        except (OSError, ValueError):
            pass
        self.query_one("#assessments-headings", Static).update(
            self.columns(("Datum", "Klasse", "Fach", "Nr. / Art", "Bezeichnung"))
        )
        listing = self.query_one("#assessments-list", OptionList)
        for index, item in enumerate(self.entries):
            listing.replace_option_prompt(str(index), self.row(item))

    def saved(self, changed: bool | None) -> None:
        if changed:
            self.reload_entries()

    @on(Button.Pressed, "#create-assessment")
    def action_create(self) -> None:
        if not load_school_classes(
            self.app_config.root, self.app_config.active_school_year
        ):
            self.notify("Bitte zuerst eine Klasse anlegen.")
            return
        self.app.push_screen(EditAssessmentScreen(), self.saved)

    @on(Button.Pressed, "#edit-assessment")
    def action_edit(self) -> None:
        if (item := self.selected()) and item.assessment.completed_on is None:
            self.app.push_screen(EditAssessmentScreen(item), self.saved)

    @on(Button.Pressed, "#delete-assessment")
    def action_delete(self) -> None:
        item = self.selected()
        if item is None:
            return

        def confirmed(result: bool | None) -> None:
            if result:
                try:
                    delete_assessment(
                        self.app_config, item.school_class_id, item.assessment.id
                    )
                except (OSError, ValueError) as error:
                    self.notify(str(error), severity="error")
                    return
                self.reload_entries()

        self.app.push_screen(
            ConfirmationScreen(
                "Leistungsnachweis löschen",
                f"{item.number}. {item.assessment.kind.label} · {item.assessment.title}\n{item.school_class_id} · {format_date(item.assessment.date)}",
                confirm_id="confirm-assessment-deletion",
                cancel_id="cancel-assessment-deletion",
            ),
            confirmed,
        )

    @on(Button.Pressed, "#complete-assessment")
    def action_complete(self) -> None:
        item = self.selected()
        if item is None:
            return
        try:
            complete_assessment(
                self.app_config, item.school_class_id, item.assessment.id
            )
        except (OSError, ValueError) as error:
            self.notify(str(error), severity="error")
            return
        self.reload_entries()
        self.notify(
            "Leistungsnachweis durchgeführt und im Unterrichtsprotokoll gespeichert."
        )

    @on(Button.Pressed, "#reopen-assessment")
    def action_reopen(self) -> None:
        item = self.selected()
        if item is None or item.assessment.completed_on is None:
            return

        def confirmed(result: bool | None) -> None:
            if not result:
                return
            try:
                reopen_assessment(
                    self.app_config, item.school_class_id, item.assessment.id
                )
            except (OSError, ValueError) as error:
                self.notify(str(error), severity="error")
                return
            self.reload_entries()

        self.app.push_screen(
            ConfirmationScreen(
                "LNW-Abschluss zurücknehmen",
                f"{item.number}. {item.assessment.kind.label} · {item.assessment.title}\nDer Protokolleintrag wird zurückgenommen und der Termin wieder geöffnet.",
                confirm_id="confirm-assessment-reopen",
                cancel_id="cancel-assessment-reopen",
            ),
            confirmed,
        )

    @on(Button.Pressed, "#close-assessments")
    def action_cancel(self) -> None:
        self.dismiss()
