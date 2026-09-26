from datetime import date
from typing import ClassVar
from uuid import uuid4

from textual import on
from textual.app import ComposeResult
from textual.widgets import Input, Label, Select, SelectionList, Static

from pult.presentation import format_date, parse_date
from pult.school.assessment import Assessment, AssessmentKind, load_assessments
from pult.school.period import load_periods
from pult.school.school_class import load_school_classes
from pult.school.subject import load_subjects
from pult.screens.base_screen import PultModalScreen
from pult.services.assessment_conflicts import assessment_conflicts, conflict_message
from pult.services.assessments import (
    ScopedAssessment,
    allowed_assessment_kinds,
    available_periods,
    store_assessment,
)
from pult.services.closures import get_default_closure_date
from pult.widgets.button import Button
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal, Vertical


class EditAssessmentScreen(PultModalScreen[bool]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(self, selected: ScopedAssessment | None = None) -> None:
        super().__init__()
        self.selected = selected

    def compose(self) -> ComposeResult:
        config = self.app_config
        self.school_classes = load_school_classes(
            config.root, config.active_school_year
        )
        self.subjects = {item.id: item.name for item in load_subjects(config.root)}
        entry = self.selected.assessment if self.selected else None
        self._last_kind = entry.kind.value if entry else "sa"
        self.periods = load_periods(config.root)
        start_period = next(
            (
                period.number
                for period in self.periods
                if entry and period.start == entry.start
            ),
            None,
        )
        self._period_context = (
            (self.selected.school_class_id, entry.subject_id, entry.date, start_period)
            if self.selected and entry
            else None
        )
        with FormDialog(
            "Leistungsnachweis bearbeiten" if entry else "Leistungsnachweis anlegen",
            id="assessment-dialog",
        ):
            with FormFields(classes="form-fields"):
                with Horizontal(classes="assessment-row"):
                    with Vertical(classes="assessment-field"):
                        yield Label("Klasse")
                        yield Select(
                            [(item.id, item.id) for item in self.school_classes],
                            value=self.selected.school_class_id
                            if self.selected
                            else self.school_classes[0].id,
                            allow_blank=False,
                            disabled=bool(entry),
                            id="assessment-class",
                        )
                    with Vertical(classes="assessment-field"):
                        yield Label("Fach")
                        yield Select(
                            [("Fach wählen", "")],
                            id="assessment-subject",
                            allow_blank=False,
                        )
                yield Label("Art")
                yield Select(
                    [],
                    prompt="Art wählen",
                    id="assessment-kind",
                )
                yield Static(
                    "", id="assessment-kind-hint", classes="form-hint", markup=False
                )
                yield Label("Bezeichnung")
                yield Input(
                    entry.title if entry else "",
                    id="assessment-title",
                    placeholder="z. B. Bruchrechnung",
                )
                with Horizontal(classes="assessment-row"):
                    with Vertical(classes="assessment-field"):
                        yield Label("Datum")
                        yield Input(
                            format_date(
                                entry.date
                                if entry
                                else get_default_closure_date(config, date.today())
                            ),
                            placeholder="TT.MM.JJJJ",
                            id="assessment-date",
                        )
                    with Vertical(classes="assessment-field"):
                        yield Label("Beginn")
                        yield Select(
                            [
                                (f"{period.number}. Stunde", period.number)
                                for period in self.periods
                            ],
                            value=(
                                start_period
                                if start_period is not None
                                else Select.NULL
                            )
                            if entry
                            else self.periods[0].number,
                            prompt="Stunde wählen",
                            id="assessment-start",
                        )
                    with Vertical(classes="assessment-field"):
                        yield Label("Dauer in Minuten")
                        yield Input(
                            str(entry.duration_minutes) if entry else "45",
                            id="assessment-duration",
                            type="integer",
                        )
                with Horizontal(classes="assessment-row assessment-bottom-row"):
                    with Vertical(classes="assessment-field"):
                        yield Label("Belegte Stunden")
                        yield SelectionList[int](id="assessment-periods")
                        yield Static(id="assessment-period-hint")
                    with Vertical(classes="assessment-field"):
                        yield Label("Verknüpfter Termin")
                        yield Select(
                            [("Keine Verknüpfung", "")],
                            id="assessment-group",
                            allow_blank=False,
                        )
            with Horizontal(classes="form-actions"):
                yield Button("Abbrechen", id="cancel-assessment")
                yield Button("Speichern", id="save-assessment", variant="primary")

    def on_mount(self) -> None:
        self.update_subjects()

    @on(Select.Changed, "#assessment-kind")
    def kind_changed(self, event: Select.Changed) -> None:
        self.update_duration(event.value)

    def update_duration(self, kind: object) -> None:
        if kind is Select.NULL or kind == self._last_kind:
            return
        self._last_kind = kind
        durations = {
            AssessmentKind.IMPROMPTU_TEST.value: 20,
            AssessmentKind.SCHOOL_EXAM.value: 45,
            AssessmentKind.ANNOUNCED_TEST.value: 30,
        }
        duration = durations.get(str(kind))
        if duration is not None:
            self.query_one("#assessment-duration", Input).value = str(duration)

    @on(Select.Changed, "#assessment-class")
    def class_changed(self) -> None:
        self.update_subjects()

    def update_subjects(self) -> None:
        class_id = self.query_one("#assessment-class", Select).value
        school_class = next(
            (item for item in self.school_classes if item.id == class_id), None
        )
        if school_class is None:
            return
        select = self.query_one("#assessment-subject", Select)
        previous = select.value
        select.set_options(
            [(self.subjects[key], key) for key in school_class.subject_ids]
        )
        desired = self.selected.assessment.subject_id if self.selected else previous
        select.value = (
            desired
            if desired in school_class.subject_ids
            else school_class.subject_ids[0]
        )
        self.update_kinds()
        self.update_groups()
        self.update_periods()

    @on(Select.Changed, "#assessment-subject")
    def subject_changed(self) -> None:
        self.update_kinds()
        self.update_groups()
        self.update_periods()

    def update_kinds(self) -> None:
        class_id = self.query_one("#assessment-class", Select).value
        subject_id = self.query_one("#assessment-subject", Select).value
        if subject_id is Select.NULL or not subject_id:
            return
        select = self.query_one("#assessment-kind", Select)
        hint = self.query_one("#assessment-kind-hint", Static)
        try:
            kinds = allowed_assessment_kinds(
                self.app_config, str(class_id), str(subject_id)
            )
        except (OSError, ValueError) as error:
            kinds = ()
            message = str(error)
        else:
            message = (
                ""
                if kinds
                else "Keine erlaubten Arten hinterlegt. Bitte die LNW-Vorgaben in den Einstellungen prüfen."
            )
        context = (class_id, subject_id, kinds)
        if context == getattr(self, "_kind_context", None):
            return
        first = not hasattr(self, "_kind_context")
        self._kind_context = context
        previous = (
            self.selected.assessment.kind.value
            if first and self.selected
            else select.value
        )
        allowed = [kind.value for kind in kinds]
        invalid_existing = (
            self.selected is not None
            and self.selected.assessment.subject_id == subject_id
            and self.selected.assessment.kind not in kinds
        )
        if invalid_existing and self.selected is not None:
            message = f"Bisher: {self.selected.assessment.kind.label} (nicht mehr erlaubt). Bitte eine erlaubte Art wählen."
        desired = (
            previous
            if previous in allowed
            else (Select.NULL if invalid_existing or not allowed else allowed[0])
        )
        with self.prevent(Select.Changed):
            select.set_options([(kind.label, kind.value) for kind in kinds])
            select.value = desired
        select.disabled = not kinds
        hint.update(message)
        hint.display = bool(message)
        self.update_duration(desired)

    @on(Input.Changed, "#assessment-date")
    def date_changed(self) -> None:
        self.update_periods()

    @on(Select.Changed, "#assessment-start")
    def start_changed(self, event: Select.Changed) -> None:
        self.update_periods()

    def update_periods(self) -> None:
        listing = self.query_one("#assessment-periods", SelectionList)
        selected = set(listing.selected)
        try:
            day = parse_date(self.query_one("#assessment-date", Input).value)
            class_id = str(self.query_one("#assessment-class", Select).value)
            subject_id = str(self.query_one("#assessment-subject", Select).value)
            periods = available_periods(self.app_config, class_id, subject_id, day)
        except (OSError, ValueError) as error:
            self.query_one("#assessment-period-hint", Static).update(str(error))
            return
        if (
            self.selected
            and (class_id, subject_id, day)
            == (
                self.selected.school_class_id,
                self.selected.assessment.subject_id,
                self.selected.assessment.date,
            )
            and not getattr(self, "_periods_initialized", False)
        ):
            selected = set(self.selected.assessment.occupied_periods)
            self._periods_initialized = True
        start = self.query_one("#assessment-start", Select).value
        context = (class_id, subject_id, day, start)
        if context != self._period_context:
            self._period_context = context
            if isinstance(start, int) and start in periods:
                selected.add(start)
        # Bestehende, inzwischen unpassende Zuordnungen bleiben sichtbar und werden beim Speichern geprüft.
        choices = sorted(set(periods) | selected)
        listing.clear_options()
        listing.add_options(
            (
                f"{period}. Stunde"
                + (" (nicht im Stundenplan)" if period not in periods else ""),
                period,
                period in selected,
            )
            for period in choices
        )
        listing.display = bool(choices)
        self.query_one("#assessment-period-hint", Static).update(
            "" if choices else "Kein eigener Unterricht."
        )

    def update_groups(self) -> None:
        config = self.app_config
        class_id = str(self.query_one("#assessment-class", Select).value)
        subject_id = self.query_one("#assessment-subject", Select).value
        entries = load_assessments(config.root, config.active_school_year, class_id)
        options = [("Keine Verknüpfung", "")]
        used = {""}
        for entry in entries:
            if entry.subject_id != subject_id or (
                self.selected and entry.id == self.selected.assessment.id
            ):
                continue
            group = entry.group_id or entry.id
            if group not in used:
                options.append((f"{format_date(entry.date)} · {entry.title}", group))
                used.add(group)
        current = (
            self.selected.assessment.group_id
            if self.selected and self.selected.assessment.subject_id == subject_id
            else None
        )
        if current and current not in used:
            options.append(("Bestehende Gruppe (ohne weiteren Termin)", current))
            used.add(current)
        select = self.query_one("#assessment-group", Select)
        select.set_options(options)
        select.value = current or ""

    @on(Button.Pressed, "#save-assessment")
    def save(self) -> None:
        def value(name: str) -> str:
            return self.query_one(f"#assessment-{name}", Input).value.strip()

        try:
            number = self.query_one("#assessment-start", Select).value
            period = next(
                (item for item in self.periods if item.number == number), None
            )
            if period is None:
                raise ValueError("Bitte eine Beginnstunde auswählen.")
            kind = self.query_one("#assessment-kind", Select).value
            if kind is Select.NULL:
                raise ValueError("Bitte eine erlaubte Art auswählen.")
            entry = Assessment(
                id=self.selected.assessment.id if self.selected else uuid4().hex,
                subject_id=str(self.query_one("#assessment-subject", Select).value),
                kind=AssessmentKind(kind),
                title=value("title"),
                date=parse_date(value("date")),
                start=period.start,
                duration_minutes=int(value("duration")),
                occupied_periods=tuple(
                    sorted(
                        self.query_one("#assessment-periods", SelectionList).selected
                    )
                ),
                group_id=str(self.query_one("#assessment-group", Select).value) or None,
                completed_on=self.selected.assessment.completed_on
                if self.selected
                else None,
            )
            store_assessment(
                self.app_config,
                str(self.query_one("#assessment-class", Select).value),
                entry,
                creating=self.selected is None,
            )
        except (OSError, TypeError, ValueError) as error:
            self.notify(str(error), severity="error")
            return
        class_id = str(self.query_one("#assessment-class", Select).value)
        try:
            conflicts = assessment_conflicts(self.app_config, class_id, entry)
        except (OSError, ValueError) as error:
            self.notify(
                f"Gespeichert. Kollisionsprüfung nicht möglich: {error}",
                severity="warning",
            )
        else:
            if conflicts:
                self.notify(
                    "\n".join(
                        conflict_message(class_id, entry, closure)
                        for closure in conflicts
                    ),
                    title="Gespeichert · Terminkonflikt",
                    severity="warning",
                    timeout=12,
                )
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-assessment")
    def action_cancel(self) -> None:
        self.dismiss(False)
