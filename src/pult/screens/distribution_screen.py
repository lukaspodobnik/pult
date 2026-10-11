from typing import ClassVar

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container
from textual.timer import Timer
from textual.widgets import Label

from pult.curriculum.sequence import Sequence
from pult.progress.queries.distribution import DistributionRow, build_distribution_plan
from pult.school.school_class import SchoolClass, load_school_classes
from pult.school.subject import Subject, load_subjects
from pult.screens.base_screen import PultScreen
from pult.services.distribution_export import export_distribution_plan
from pult.services.exports import export_error_message
from pult.services.progress import PlanningData, load_planning_data
from pult.views.distribution_view import DistributionView
from pult.widgets.footer import PultFooter
from pult.widgets.navigation import ViewPicker
from pult.widgets.scrolling import Horizontal, OptionList, Vertical


class DistributionScreen(PultScreen[None]):
    BINDINGS: ClassVar = [
        ("escape", "close", "Zurück"),
        ("x", "export_pdf", "PDF exportieren"),
    ]

    def __init__(
        self,
        initial_school_class_id: str | None = None,
        *,
        subject_id: str | None = None,
    ) -> None:
        super().__init__()
        self.initial_school_class_id = initial_school_class_id
        self.subject_id = subject_id
        self.school_classes: list[SchoolClass] = []
        self.school_classes_by_id: dict[str, SchoolClass] = {}
        self.subjects: list[Subject] = []
        self.sequences: list[Sequence] = []
        self._view_timer: Timer | None = None
        self._pending_target: tuple[str, str] | None = None
        self._displayed_target: tuple[str, str] | None = None
        self._exporting = False
        # Nur für diesen geöffneten Screen: erneutes Öffnen liest aktuelle Dateien.
        self._planning_cache: dict[str, PlanningData] = {}
        self._views: dict[tuple[str, str], DistributionView] = {}

    def compose(self) -> ComposeResult:
        with Horizontal(id="distribution-screen"):
            with Vertical(id="distribution-navigation"):
                picker = ViewPicker(id="distribution-class-picker")
                picker.border_title = "KLASSEN"
                yield picker

            content = Container(id="distribution-content")
            content.border_title = "Stoffverteilungsplan"
            yield content

        yield PultFooter()

    async def on_mount(self) -> None:
        config = self.app_config
        try:
            self.school_classes = load_school_classes(
                config.root,
                config.active_school_year,
            )
            self.school_classes_by_id = {
                school_class.id: school_class for school_class in self.school_classes
            }
            self.subjects = load_subjects(config.root)
            self.sequences = self.sequence_library
        except (OSError, KeyError, ValueError) as error:
            self.notify(
                f"Der Stoffverteilungsplan konnte nicht geladen werden: {error}",
                severity="error",
            )
            return

        picker = self.query_one("#distribution-class-picker", ViewPicker)
        # Die initiale Auswahl wird unten genau einmal ausdrücklich angezeigt.
        with self.prevent(OptionList.OptionHighlighted):
            picker.refresh_options(
                self.school_classes, self.subjects, include_home=False
            )
            picker.focus()

            if not self.school_classes:
                await self._show_empty_state("Es wurden noch keine Klassen angelegt.")
                return

            selected_id = (
                self.initial_school_class_id
                if self.initial_school_class_id in self.school_classes_by_id
                else self.school_classes[0].id
            )
            targets = list(picker.class_subjects_by_option_id.values())
            picker.highlighted = next(
                (
                    index
                    for index, (class_id, subject_id) in enumerate(targets)
                    if class_id == selected_id and subject_id == self.subject_id
                ),
                next(
                    index
                    for index, (class_id, _) in enumerate(targets)
                    if class_id == selected_id
                ),
            )
            self.subject_id = targets[picker.highlighted][1]
        await self.show_distribution(self.school_classes_by_id[selected_id])

    @on(OptionList.OptionHighlighted, "#distribution-class-picker")
    def school_class_highlighted(
        self,
        event: OptionList.OptionHighlighted,
    ) -> None:
        if event.option_id is None:
            return

        picker = self.query_one("#distribution-class-picker", ViewPicker)
        self._pending_target = picker.class_subjects_by_option_id[event.option_id]
        if self._view_timer is not None:
            self._view_timer.stop()
        self._view_timer = self.set_timer(0.08, self._show_pending_plan)

    async def _show_pending_plan(self) -> None:
        self._view_timer = None
        if self._pending_target is None or self.app.screen is not self:
            return
        school_class_id, self.subject_id = self._pending_target
        self._pending_target = None
        school_class = self.school_classes_by_id.get(school_class_id)
        if school_class is not None:
            await self.show_distribution(school_class)

    async def show_distribution(self, school_class: SchoolClass) -> None:
        self._displayed_target = None
        config = self.app_config
        try:
            progress = self._planning_cache.get(school_class.id)
            if progress is None:
                progress = load_planning_data(
                    config, school_class.id, sequences=self.sequences
                )
                self._planning_cache[school_class.id] = progress
        except (OSError, KeyError, StopIteration, ValueError) as error:
            self.notify(
                f"Der Stoffverteilungsplan für {school_class.id} konnte nicht geladen werden: {error}",
                severity="error",
            )
            return

        content = self.query_one("#distribution-content", Container)
        subject = next(s for s in self.subjects if s.id == self.subject_id)
        content.border_title = (
            f"Stoffverteilungsplan · {school_class.id} · {subject.name}"
        )
        key = (school_class.id, subject.id)
        for view in self._views.values():
            view.display = False
        if key in self._views:
            self._views[key].display = True
            self._displayed_target = key
            self.refresh_bindings()
            return
        try:
            rows = build_distribution_plan(
                progress,
                school_class.id,
                subject.id,
                subject_labels={s.id: s.short_name for s in self.subjects},
            )
        except (KeyError, StopIteration, ValueError) as error:
            await self._show_empty_state(
                f"Der Plan konnte nicht berechnet werden: {error}"
            )
            return
        view = DistributionView(rows)
        self._views[key] = view
        await content.mount(view)
        self._displayed_target = key
        self.refresh_bindings()

    async def _show_empty_state(self, message: str) -> None:
        self._displayed_target = None
        self._views.clear()
        self.refresh_bindings()
        content = self.query_one("#distribution-content", Container)
        await content.remove_children()
        await content.mount(Label(message, classes="distribution-empty"))

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "export_pdf":
            return (
                self._displayed_target is not None
                and not self._exporting
                and self._pending_target is None
            )
        return True

    def action_export_pdf(self) -> None:
        if not self.check_action("export_pdf", ()):
            return
        assert self._displayed_target is not None
        school_class_id, subject_id = self._displayed_target
        subject = next(s for s in self.subjects if s.id == subject_id)
        view = self._views[self._displayed_target]
        self._exporting = True
        self.refresh_bindings()
        self._export_pdf(school_class_id, subject.id, subject.name, view.rows)

    @work(group="pdf-export", exit_on_error=False)
    async def _export_pdf(
        self,
        school_class_id: str,
        subject_id: str,
        subject_name: str,
        rows: tuple[DistributionRow, ...],
    ) -> None:
        try:
            path = await export_distribution_plan(
                self.pult_app.document_renderer,
                self.app_config,
                school_class_id=school_class_id,
                subject_id=subject_id,
                subject_name=subject_name,
                rows=rows,
            )
            self.notify(f"PDF gespeichert: {path}", timeout=10)
        except Exception as error:
            self.notify(export_error_message(error), severity="error")
        finally:
            self._exporting = False
            self.refresh_bindings()

    def action_close(self) -> None:
        if self._view_timer is not None:
            self._view_timer.stop()
        self.dismiss()
