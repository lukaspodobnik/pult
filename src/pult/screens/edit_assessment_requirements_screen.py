from dataclasses import replace
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.widgets import Input, Label, Select, SelectionList, Static

from pult.presentation import format_school_year
from pult.school.assessment import AssessmentKind
from pult.school.assessment_requirements import (
    AssessmentCategory,
    AssessmentMinimum,
    AssessmentRequirement,
    assessment_category,
    get_assessment_requirements_path,
    save_assessment_requirements,
)
from pult.school.calendar import load_school_calendar
from pult.screens.base_screen import PultModalScreen
from pult.widgets.button import Button
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal


class AssessmentKindsScreen(PultModalScreen[tuple[AssessmentKind, ...] | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]
    DEFAULT_CSS = """
    AssessmentKindsScreen #requirement-kinds { height: 6; }
    """

    def __init__(self, title: str, kinds: tuple[AssessmentKind, ...]) -> None:
        super().__init__()
        self.title_text = title
        self.kinds = kinds

    def compose(self) -> ComposeResult:
        with FormDialog("ERLAUBTE ARTEN", id="requirement-kinds-dialog"):
            with FormFields(classes="form-fields"):
                yield Static(self.title_text, markup=False)
                yield SelectionList(
                    *(
                        (kind.label, kind, kind in self.kinds)
                        for kind in AssessmentKind
                    ),
                    id="requirement-kinds",
                )
            with Horizontal(classes="form-actions"):
                yield Button("Abbrechen", id="cancel-kinds")
                yield Button("Übernehmen", id="apply-kinds", variant="primary")

    @on(Button.Pressed, "#cancel-kinds")
    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#apply-kinds")
    def apply(self) -> None:
        selected = self.query_one(SelectionList).selected
        self.dismiss(tuple(kind for kind in AssessmentKind if kind in selected))


class RequirementRow(Horizontal):
    def __init__(
        self, entry: AssessmentRequirement, subject_name: str, index: int
    ) -> None:
        super().__init__(id=f"requirement-{index}", classes="requirement-row")
        self.entry = entry
        self.subject_name = subject_name
        self.index = index
        self.kinds = entry.allowed_kinds

    def compose(self) -> ComposeResult:
        yield Label(str(self.entry.grade_level), classes="requirement-grade")
        for category in AssessmentCategory:
            count = self.entry.minimum_for(category)
            allowed = any(assessment_category(kind) == category for kind in self.kinds)
            yield Input(
                "" if count is None else str(count),
                placeholder="—",
                disabled=not allowed,
                id=f"{category.value}-{self.index}",
                classes="requirement-minimum",
            )
        yield Button(self.kinds_label(), classes="requirement-kinds-button")

    def kinds_label(self) -> str:
        return " · ".join(kind.abbreviation for kind in self.kinds) or "Keine Arten"

    @on(Button.Pressed)
    def edit_kinds(self, event: Button.Pressed) -> None:
        event.stop()
        self.app.push_screen(
            AssessmentKindsScreen(
                f"{self.subject_name} · Jahrgangsstufe {self.entry.grade_level}",
                self.kinds,
            ),
            self.kinds_changed,
        )

    def kinds_changed(self, kinds: tuple[AssessmentKind, ...] | None) -> None:
        if kinds is None:
            return
        self.kinds = kinds
        self.query_one(Button).label = self.kinds_label()
        for category in AssessmentCategory:
            field = self.query_one(f"#{category.value}-{self.index}", Input)
            allowed = any(assessment_category(kind) == category for kind in kinds)
            field.disabled = not allowed
            field.placeholder = "—"
            if not allowed:
                field.value = ""

    def read_entry(self) -> AssessmentRequirement:
        minimums = []
        for category in AssessmentCategory:
            field = self.query_one(f"#{category.value}-{self.index}", Input)
            value = field.value.strip()
            if not value:
                continue
            if not value.isascii() or not value.isdecimal():
                raise ValueError(
                    f"{self.subject_name}, Jahrgangsstufe {self.entry.grade_level}: "
                    "Bitte eine ganze Zahl ab 0 eingeben oder das Feld leer lassen."
                )
            minimums.append(AssessmentMinimum(category, int(value)))
        return replace(self.entry, allowed_kinds=self.kinds, minimums=tuple(minimums))


class EditAssessmentRequirementsScreen(PultModalScreen[bool]):
    """Bearbeite Jahresvorgaben als Entwurf; erst Speichern schreibt alle Fächer."""

    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]
    DEFAULT_CSS = """
    EditAssessmentRequirementsScreen .requirement-row { height: 3; }
    EditAssessmentRequirementsScreen .requirement-grade { width: 7; padding-top: 1; }
    EditAssessmentRequirementsScreen .requirement-minimum { width: 10; margin-right: 1; }
    EditAssessmentRequirementsScreen .requirement-kinds-button { width: 1fr; min-width: 0; }
    EditAssessmentRequirementsScreen #requirements-headings {
        height: 2; margin-top: 1; border-bottom: solid $foreground-muted;
        color: $foreground-muted;
    }
    EditAssessmentRequirementsScreen .heading-grade { width: 7; }
    EditAssessmentRequirementsScreen .heading-minimum { width: 11; }
    EditAssessmentRequirementsScreen .heading-kinds { width: 1fr; }
    """

    def __init__(
        self, year: str, entries: list[AssessmentRequirement], subjects: dict[str, str]
    ) -> None:
        super().__init__()
        self.year = year
        self.entries = entries
        self.subjects = subjects
        self.subject_ids = list(dict.fromkeys(entry.subject_id for entry in entries))

    def compose(self) -> ComposeResult:
        with FormDialog("LEISTUNGSNACHWEISE", id="requirements-dialog", wide=True):
            with FormFields(classes="form-fields"):
                yield Static(
                    f"Schuljahr {format_school_year(self.year)} · Speichern gilt direkt.\n"
                    "Jahresminimum: Groß = SA, Klein = EX + AKL. Leer = keine Vorgabe.",
                    classes="form-hint",
                )
                if self.subject_ids:
                    yield Label("Fach", classes="field-label")
                    yield Select(
                        [
                            (self.subjects.get(key, key), key)
                            for key in self.subject_ids
                        ],
                        value=self.subject_ids[0],
                        allow_blank=False,
                        id="requirements-subject",
                    )
                    with Horizontal(id="requirements-headings"):
                        yield Static("Jgst.", classes="heading-grade")
                        yield Static("Groß", classes="heading-minimum")
                        yield Static("Klein", classes="heading-minimum")
                        yield Static("Erlaubte Arten", classes="heading-kinds")
                    for index, entry in enumerate(self.entries):
                        row = RequirementRow(
                            entry,
                            self.subjects.get(entry.subject_id, entry.subject_id),
                            index,
                        )
                        row.display = entry.subject_id == self.subject_ids[0]
                        yield row
                else:
                    yield Static("Für dieses Schuljahr sind keine Vorgaben hinterlegt.")
                yield Static("", id="requirements-error", markup=False)
            with Horizontal(classes="form-actions"):
                yield Button("Abbrechen", id="cancel-requirements")
                yield Button("Speichern", id="save-requirements", variant="primary")

    @on(Select.Changed, "#requirements-subject")
    def subject_changed(self, event: Select.Changed) -> None:
        for row in self.query(RequirementRow):
            row.display = row.entry.subject_id == event.value
        count = sum(entry.subject_id == event.value for entry in self.entries)
        self.query_one("#requirements-dialog").styles.height = 18 + 3 * count

    @on(Button.Pressed, "#cancel-requirements")
    def action_cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#save-requirements")
    def save(self) -> None:
        try:
            entries = [row.read_entry() for row in self.query(RequirementRow)]
            load_school_calendar(self.app_config.root, self.year)
            path = get_assessment_requirements_path(self.app_config.root, self.year)
            path.parent.mkdir(parents=True, exist_ok=True)
            save_assessment_requirements(self.app_config.root, self.year, entries)
        except (OSError, ValueError) as error:
            self.query_one("#requirements-error", Static).update(str(error))
            self.notify(f"LNW-Vorgaben nicht gespeichert: {error}", severity="error")
            return
        self.notify(f"LNW-Vorgaben für {format_school_year(self.year)} gespeichert.")
        self.dismiss(True)
