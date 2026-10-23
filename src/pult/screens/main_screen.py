import asyncio
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.events import DescendantFocus
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import ContentSwitcher

from pult.config import AppConfig
from pult.curriculum.sequence import Sequence
from pult.presentation import UNTITLED_LESSON, format_compact_date
from pult.progress.class_progress import ClassProgress
from pult.progress.commands import (
    ProgressCommandError,
    cancel_scheduled_lesson,
    complete_lesson,
    continue_lesson,
    record_spontaneous_lesson,
    skip_lesson,
    undo_last_entry,
)
from pult.progress.queries import PlannedLesson
from pult.progress.queries.assessments import PlannedAssessment, next_event
from pult.school.school_class import SchoolClass, load_school_classes
from pult.school.subject import load_subjects
from pult.screens.base_screen import PultScreen
from pult.screens.management.edit_assessments_screen import EditAssessmentsScreen
from pult.screens.management.edit_classes_screen import EditClassesScreen
from pult.screens.management.edit_closures_screen import EditClosuresScreen
from pult.screens.management.edit_timetable_screen import EditTimetableScreen
from pult.screens.progress.cancel_lesson_screen import CancelLessonScreen
from pult.screens.progress.confirm_undo_screen import ConfirmUndoScreen
from pult.screens.progress.distribution_screen import DistributionScreen
from pult.screens.progress.lesson_progress_flow import LessonProgressFlow
from pult.screens.progress.spontaneous_lesson_screen import SpontaneousLessonScreen
from pult.screens.progress.teaching_log_screen import TeachingLogScreen
from pult.screens.settings.settings_screen import SettingsScreen
from pult.screens.teaching.curriculum_screen import CurriculumScreen
from pult.screens.teaching.lesson_screen import LessonScreen
from pult.screens.teaching.sequence_library_screen import SequenceLibraryScreen
from pult.services.assessments import complete_assessment, reopen_assessment
from pult.services.dashboard import (
    HomeViewData,
    load_home_view_data,
    load_school_class_view_data,
)
from pult.services.progress import (
    PlannedLessonContext,
    get_planned_lesson_context,
    load_class_progress_data,
    load_planning_data,
    save_class_progress_data,
)
from pult.views.home_view import HomeView
from pult.views.school_class_view import SchoolClassView
from pult.widgets.app_logo import AppLogo
from pult.widgets.footer import PultFooter
from pult.widgets.navigation import ManagementPicker, TeachingPicker, ViewPicker
from pult.widgets.scrolling import Horizontal, OptionList, Vertical
from pult.widgets.startup_logo import StartupLogo


class MainScreen(PultScreen[None]):
    VIEW_DEBOUNCE_SECONDS: ClassVar[float] = 0.06
    BINDINGS: ClassVar = [
        ("o", "open_next_lesson", "Unterricht öffnen"),
        ("n", "complete_next_lesson", "Abschließen"),
        ("s", "skip_next_lesson", "Überspringen"),
        ("c", "continue_next_lesson", "Fortsetzen"),
        ("a", "cancel_next_lesson", "Ausfall"),
        ("t", "record_spontaneous_lesson", "Spontanunterricht"),
        ("z", "add_extra_lesson", "Zusätzlicher Termin"),
        ("p", "undo_last_entry", "Rückgängig"),
        ("u", "show_teaching_log", "Protokoll"),
        ("w", "change_active_sequence", "Sequenz wechseln"),
        ("f2", "go_home", "Übersicht"),
    ]

    def __init__(self, *, startup: bool = False) -> None:
        super().__init__()
        self.startup_active = startup
        self._startup_faded = False
        self._startup_ready = False
        self._startup_revealing = False
        self.school_classes_by_id: dict[str, SchoolClass] = {}
        self.active_school_class_id: str | None = None
        self.active_subject_id: str | None = None
        self._pending_view_id: str | None = None
        self._last_assessment_completion: tuple[str, str] | None = None
        self._view_timer: Timer | None = None
        self._lesson_progress_flow = LessonProgressFlow(
            self, self.save_progress_and_refresh
        )

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="navigation"):
                yield AppLogo(id="app-logo")
                yield ViewPicker(id="view-picker")
                yield TeachingPicker(id="teaching-picker")
                yield ManagementPicker(id="management-picker")

            content = ContentSwitcher(id="content")
            content.can_focus_children = False
            yield content

        yield PultFooter()
        if self.startup_active:
            yield StartupLogo()

    def on_mount(self) -> None:
        if self.startup_active:
            self.query_one("#main").styles.opacity = 0
            self.query_one(PultFooter).styles.opacity = 0
            self.call_after_refresh(self._start_logo_fade)
        self.refresh_view_picker()
        self.query_one("#view-picker", ViewPicker).focus()

    def _start_logo_fade(self) -> None:
        self.query_one(StartupLogo).styles.animate(
            "text_opacity",
            0.0,
            duration=0.65,
            delay=0.4,
            easing="in_out_sine",
            on_complete=self._logo_faded,
        )

    def _logo_faded(self) -> None:
        self._startup_faded = True
        self._reveal_startup()

    def _startup_view_ready(self) -> None:
        self._startup_ready = True
        self._reveal_startup()

    def _reveal_startup(self) -> None:
        if (
            self.startup_active
            and self._startup_faded
            and self._startup_ready
            and not self._startup_revealing
        ):
            self._startup_revealing = True
            self.query_one(StartupLogo).remove()
            self.query_one("#main").styles.animate(
                "opacity",
                1.0,
                duration=0.25,
                easing="out_sine",
                on_complete=self._finish_startup,
            )
            self.query_one(PultFooter).styles.animate(
                "opacity",
                1.0,
                duration=0.25,
                easing="out_sine",
            )

    def _finish_startup(self) -> None:
        self.startup_active = False

    def on_resize(self) -> None:
        self.call_after_refresh(self.align_dashboard)

    def align_dashboard(self) -> None:
        # Die Übersicht zeigt sechs Stunden; ANSICHTEN erhält dieselbe Höhe.
        height = min(27, max(12, self.size.height - 17))
        for widget in self.query(".sequence-list"):
            widget.styles.height = height
        for widget in self.query("#view-picker"):
            widget.styles.height = (
                21 if self.active_school_class_id is None else height - 7
            )

    def action_go_home(self) -> None:
        """Wähle die Übersicht und setze den Fokus zurück auf den Ansichtenpicker."""
        picker = self.query_one("#view-picker", ViewPicker)
        picker.highlighted = picker.get_option_index("home")
        picker.focus()

    def refresh_view_picker(self) -> None:
        view_picker = self.query_one("#view-picker", ViewPicker)
        highlighted_option_id = None
        if view_picker.highlighted is not None:
            option = view_picker.get_option_at_index(view_picker.highlighted)
            if option.id is not None:
                highlighted_option_id = str(option.id)

        self.refresh_school_classes()
        view_picker.refresh_options(
            list(self.school_classes_by_id.values()),
            load_subjects(self.app_config.root),
            highlighted_option_id,
        )

    def refresh_school_classes(self) -> None:
        config = self.app_config
        school_classes = load_school_classes(config.root, config.active_school_year)
        self.school_classes_by_id = {
            school_class.id: school_class for school_class in school_classes
        }

    @on(OptionList.OptionHighlighted, "#view-picker")
    def view_picker_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Merke die Auswahl; erst nach einer kurzen Ruhephase wird sie aufgebaut."""
        self._pending_view_id = event.option_id
        self._schedule_view_change()
        # Die Befehlssperre wird von check_action bei jeder Eingabe geprüft.
        # Den Footer erst nach dem Wechsel aktualisieren, nicht pro Pfeiltaste.

    def _schedule_view_change(self) -> None:
        if self._view_timer is not None:
            self._view_timer.stop()
            self._view_timer = None
        if self._pending_view_id is not None:
            self._view_timer = self.set_timer(
                self.VIEW_DEBOUNCE_SECONDS, self._show_pending_view
            )

    async def _show_pending_view(self) -> None:
        self._view_timer = None
        option_id = self._pending_view_id
        if option_id is None or self.app.screen is not self:
            return
        try:
            if option_id == "home":
                await self.show_home_view()
            else:
                target = self.query_one(ViewPicker).class_subjects_by_option_id.get(
                    option_id
                )
                if target is not None:
                    class_id, subject_id = target
                    school_class = self.school_classes_by_id.get(class_id)
                    if school_class is not None:
                        await self.show_school_class_view(school_class, subject_id)
        finally:
            self._pending_view_id = None
            self.refresh_bindings()
            if self.startup_active:
                self.call_after_refresh(self._startup_view_ready)

    def on_screen_suspend(self) -> None:
        if self._view_timer is not None:
            self._view_timer.stop()
            self._view_timer = None

    def on_screen_resume(self) -> None:
        self._schedule_view_change()

    def on_unmount(self) -> None:
        if self._view_timer is not None:
            self._view_timer.stop()

    async def switch_view(self, view: Widget) -> None:
        """Binde eine View einmal ein und schalte anschließend nur ihre Sichtbarkeit."""
        if not self.app.is_running:
            return
        content = self.query_one("#content", ContentSwitcher)
        if not view.is_mounted:
            await content.add_content(view, id=type(view).__name__)
        if self.app.is_running:
            content.current = view.id

    async def show_home_view(self) -> None:
        """Lade alle Dashboarddaten neu und zeige anschließend die HomeView."""
        self.active_school_class_id = None
        self.active_subject_id = None
        config = self.app_config

        def load_dashboard() -> HomeViewData:
            return load_home_view_data(config, sequences=self.sequence_library)

        try:
            if self.startup_active:
                data = await asyncio.to_thread(load_dashboard)
            else:
                data = load_dashboard()
        except (OSError, KeyError, StopIteration, ValueError) as error:
            self.notify(
                f"Die Übersicht konnte nicht geladen werden: {error}", severity="error"
            )
            return

        if not self.app.is_running:
            return
        self.school_classes_by_id = {
            school_class.id: school_class for school_class in data.school_classes
        }
        views = self.query(HomeView)
        if views:
            view = views.first()
            await view.update_data(
                data.timetable_entries,
                data.subjects,
                data.periods,
                data.sequences,
                data.dashboard,
            )
        else:
            view = HomeView(
                data.timetable_entries,
                data.subjects,
                data.periods,
                data.sequences,
                data.dashboard,
            )
        await self.switch_view(view)
        if not self.app.is_running:
            return
        # Gleiche Rahmenhöhen, auch wenn die Anzahl der Stunden geändert wird.
        self.align_dashboard()
        view.refresh_time_highlight()
        if self._pending_view_id is None:
            self.refresh_bindings()

    @on(HomeView.DashboardRefreshRequested)
    async def refresh_home_dashboard(
        self,
        _: HomeView.DashboardRefreshRequested,
    ) -> None:
        if self.app.screen is self and self.active_school_class_id is None:
            await self.show_home_view()

    async def show_school_class_view(
        self, school_class: SchoolClass, subject_id: str | None = None
    ) -> None:
        """Lade und validiere alle Daten für die Ansicht einer Klasse."""
        config = self.app_config
        try:
            data = load_school_class_view_data(
                config,
                school_class.id,
                subject_id,
                preferred_subject_id=(
                    self.active_subject_id
                    if self.active_school_class_id == school_class.id
                    else None
                ),
                sequences=self.sequence_library,
            )
        except (OSError, KeyError, StopIteration, ValueError) as error:
            self.notify(
                f"Die Klassenansicht konnte nicht geladen werden: {error}",
                severity="error",
            )
            return

        self.active_school_class_id = data.school_class.id
        self.active_subject_id = data.subject_id
        views = self.query(SchoolClassView)
        if views:
            view = views.first()
            await view.update_data(
                data.school_class, data.subjects, data.progress_summaries
            )
        else:
            view = SchoolClassView(
                data.school_class, data.subjects, data.progress_summaries
            )
        await self.switch_view(view)
        if self not in self.app.screen_stack:
            return
        self.align_dashboard()
        if self._pending_view_id is None:
            self.refresh_bindings()

    def check_action(
        self,
        action: str,
        parameters: tuple[object, ...],
    ) -> bool | None:
        if action == "go_home":
            return True
        if isinstance(
            self.app.focused, (ManagementPicker, TeachingPicker)
        ) and action in {
            "complete_next_lesson",
            "skip_next_lesson",
            "continue_next_lesson",
            "cancel_next_lesson",
            "record_spontaneous_lesson",
            "add_extra_lesson",
            "undo_last_entry",
            "change_active_sequence",
            "show_teaching_log",
            "open_next_lesson",
        }:
            return False
        if self._pending_view_id is not None and any(
            (binding[1] if isinstance(binding, tuple) else binding.action) == action
            for binding in self.BINDINGS
        ):
            # Während Highlight und Ansicht auseinanderliegen, keine falsche Klasse ändern.
            return None
        if action in {
            "skip_next_lesson",
            "continue_next_lesson",
            "cancel_next_lesson",
            "record_spontaneous_lesson",
        } and isinstance(self.displayed_next_lesson(), PlannedAssessment):
            return False
        if action == "undo_last_entry" and self.active_school_class_id is None:
            return self._last_assessment_completion is not None
        if action == "open_next_lesson":
            return self.displayed_next_lesson() is not None
        if action in {
            "undo_last_entry",
            "change_active_sequence",
            "show_teaching_log",
        }:
            return self.active_school_class_id is not None
        return super().check_action(action, parameters)

    @on(DescendantFocus)
    def refresh_focused_bindings(self) -> None:
        self.refresh_bindings()

    def displayed_next_lesson(self) -> PlannedLesson | PlannedAssessment | None:
        """Verwende genau die Stunde der sichtbaren Übersicht, ohne neu zu planen."""
        if self.active_school_class_id is None:
            views = self.query(HomeView)
            return (
                next_event(
                    views.first().dashboard.next_planned_lesson,
                    views.first().dashboard.next_scheduled_assessment,
                )
                if views
                else None
            )
        views = self.query(SchoolClassView)
        if not views:
            return None
        return next(
            (
                next_event(
                    summary.next_planned_lesson, summary.next_scheduled_assessment
                )
                for summary in views.first().progress_summaries
                if summary.subject_id == self.active_subject_id
            ),
            None,
        )

    def action_open_next_lesson(self) -> None:
        if not self.check_action("open_next_lesson", ()):
            return
        planned = self.displayed_next_lesson()
        if planned is None:
            return
        if isinstance(planned, PlannedAssessment):
            screen = EditAssessmentsScreen()
            screen.selected_key = (planned.school_class_id, planned.assessment.id)
            self.app.push_screen(screen, self.timetable_edit_finished)
            return
        sequence = next(
            (
                sequence
                for sequence in self.sequence_library
                if (sequence.grade_level, sequence.subject_id, sequence.id)
                == (planned.grade_level, planned.subject_id, planned.sequence_id)
            ),
            None,
        )
        if sequence is None or not any(
            lesson.id == planned.lesson.id for lesson in sequence.lessons
        ):
            self.notify(
                "Die angezeigte Stunde ist nicht mehr verfügbar.", severity="warning"
            )
            return
        self.app.push_screen(
            LessonScreen(sequence, planned.lesson.id), self.lesson_viewer_closed
        )

    async def lesson_viewer_closed(self, _: Sequence | None) -> None:
        await self.refresh_current_view()

    async def refresh_current_view(self) -> None:
        """Aktualisiere die Daten der momentan aktiven Home- oder Klassenansicht."""
        if self.active_school_class_id is None:
            await self.show_home_view()
            return

        await self.show_school_class_view(
            self.school_classes_by_id[self.active_school_class_id]
        )

    async def save_progress_and_refresh(
        self,
        school_class: SchoolClass,
        progress: ClassProgress,
        sequences: list[Sequence],
    ) -> None:
        """Validiere und speichere Fortschritt und aktualisiere danach die View."""
        self._last_assessment_completion = None
        save_class_progress_data(
            self.app_config, school_class, progress, sequences=sequences
        )
        await self.refresh_current_view()

    def load_planned_lesson_context(self) -> PlannedLessonContext | None:
        """Lade den Kontext für die nächste globale oder klassenbezogene Lesson."""
        if isinstance(self.displayed_next_lesson(), PlannedAssessment):
            self.notify(
                "Für einen Leistungsnachweis bitte Abschließen oder die Terminverwaltung verwenden."
            )
            return None
        config = self.app_config

        try:
            data = load_planning_data(
                config, self.active_school_class_id, sequences=self.sequence_library
            )
            self.school_classes_by_id.update(
                {school_class.id: school_class for school_class in data.school_classes}
            )
            context = get_planned_lesson_context(
                data, self.active_school_class_id, self.active_subject_id
            )
        except (OSError, KeyError, ValueError) as error:
            self.notify(str(error), severity="error")
            return None

        if context is None:
            self.notify(
                "Keine offene Unterrichtsstunde gefunden. Prüfe Stundenplan, Sequenzfortschritt und Schuljahr.",
                severity="warning",
            )
            return None

        return context

    async def action_complete_next_lesson(self) -> None:
        planned = self.displayed_next_lesson()
        if isinstance(planned, PlannedAssessment):
            try:
                complete_assessment(
                    self.app_config, planned.school_class_id, planned.assessment.id
                )
            except (OSError, ValueError) as error:
                self.notify(str(error), severity="error")
                return
            self._last_assessment_completion = (
                planned.school_class_id,
                planned.assessment.id,
            )
            await self.refresh_current_view()
            self.notify(f"{planned.label}: durchgeführt und protokolliert.")
            return
        context = self.load_planned_lesson_context()
        if context is None:
            return

        try:
            result = complete_lesson(
                context.progress,
                context.planned_lesson,
                context.sequences,
            )
        except ProgressCommandError as error:
            self.notify(str(error), severity="error")
            return

        await self._lesson_progress_flow.handle_result(
            context.school_class,
            context.planned_lesson.lesson.title,
            context.sequences,
            result,
            action_description="abgeschlossen",
        )

    async def action_skip_next_lesson(self) -> None:
        context = self.load_planned_lesson_context()
        if context is None:
            return

        try:
            result = skip_lesson(
                context.progress,
                context.planned_lesson,
                context.sequences,
            )
        except ProgressCommandError as error:
            self.notify(str(error), severity="error")
            return

        await self._lesson_progress_flow.handle_result(
            context.school_class,
            context.planned_lesson.lesson.title,
            context.sequences,
            result,
            action_description="übersprungen",
        )

    async def action_continue_next_lesson(self) -> None:
        context = self.load_planned_lesson_context()
        if context is None:
            return

        try:
            progress = continue_lesson(
                context.progress,
                context.planned_lesson,
                context.sequences,
            )
            await self.save_progress_and_refresh(
                context.school_class,
                progress,
                context.sequences,
            )
        except (OSError, ProgressCommandError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        self.notify(
            f"{context.school_class.id}: "
            f"'{context.planned_lesson.lesson.title or UNTITLED_LESSON}' wird fortgesetzt."
        )

    def action_cancel_next_lesson(self) -> None:
        context = self.load_planned_lesson_context()
        if context is None:
            return

        async def cancellation_entered(comment: str | None) -> None:
            if comment is None:
                return

            try:
                progress = cancel_scheduled_lesson(
                    context.progress,
                    context.planned_lesson,
                    context.sequences,
                    comment,
                )
                await self.save_progress_and_refresh(
                    context.school_class,
                    progress,
                    context.sequences,
                )
            except (OSError, ProgressCommandError, ValueError) as error:
                self.notify(str(error), severity="error")
                return

            self.notify(
                f"{context.school_class.id}: Ausfall von "
                f"'{context.planned_lesson.lesson.title or UNTITLED_LESSON}' eingetragen."
            )

        self.app.push_screen(
            CancelLessonScreen(
                school_class_id=(
                    context.school_class.id
                    if self.active_school_class_id is None
                    else None
                )
            ),
            cancellation_entered,
        )

    def action_record_spontaneous_lesson(self) -> None:
        context = self.load_planned_lesson_context()
        if context is None:
            return

        async def description_entered(description: str | None) -> None:
            if description is None:
                return
            try:
                progress = record_spontaneous_lesson(
                    context.progress,
                    context.planned_lesson,
                    context.sequences,
                    description,
                )
                await self.save_progress_and_refresh(
                    context.school_class, progress, context.sequences
                )
            except (OSError, ProgressCommandError, ValueError) as error:
                self.notify(str(error), severity="error")
                return
            self.notify(f"{context.school_class.id}: Spontanunterricht eingetragen.")

        planned = context.planned_lesson
        self.app.push_screen(
            SpontaneousLessonScreen(
                f"{context.school_class.id} · "
                f"{format_compact_date(planned.date)} · {planned.period}. Stunde"
            ),
            description_entered,
        )

    def action_add_extra_lesson(self) -> None:
        self._lesson_progress_flow.open_extra_lesson(
            fixed_school_class_id=self.active_school_class_id,
            fixed_subject_id=self.active_subject_id,
        )

    async def action_undo_last_entry(self) -> None:
        if self.active_school_class_id is None and self._last_assessment_completion:
            class_id, assessment_id = self._last_assessment_completion

            async def confirmed(result: bool | None) -> None:
                if result:
                    try:
                        reopen_assessment(self.app_config, class_id, assessment_id)
                    except (OSError, ValueError) as error:
                        self.notify(str(error), severity="error")
                        return
                    self._last_assessment_completion = None
                    await self.refresh_current_view()

            self.app.push_screen(
                ConfirmUndoScreen(class_id, "Leistungsnachweis"), confirmed
            )
            return
        if self.active_school_class_id is None or self.active_subject_id is None:
            return

        subject_id = self.active_subject_id
        config = self.app_config
        school_class = self.school_classes_by_id[self.active_school_class_id]
        try:
            data = load_class_progress_data(
                config, school_class, sequences=self.sequence_library
            )
            sequences, progress = data.sequences, data.progress
            subject_name = next(
                subject.name
                for subject in load_subjects(config.root)
                if subject.id == subject_id
            )
        except (OSError, KeyError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        if not any(entry.subject_id == subject_id for entry in progress.entries):
            self.notify(
                "Für dieses Fach gibt es keinen Protokolleintrag zum Zurücknehmen.",
                severity="warning",
            )
            return

        async def undo_confirmed(confirmed: bool | None) -> None:
            if not confirmed:
                return

            try:
                updated_progress = undo_last_entry(progress, subject_id=subject_id)
                await self.save_progress_and_refresh(
                    school_class,
                    updated_progress,
                    sequences,
                )
            except (OSError, ProgressCommandError, ValueError) as error:
                self.notify(str(error), severity="error")
                return

            self.notify(f"{school_class.id}: Letzten Eintrag zurückgenommen.")

        self.app.push_screen(
            ConfirmUndoScreen(school_class.id, subject_name),
            undo_confirmed,
        )

    def action_change_active_sequence(self) -> None:
        if self.active_school_class_id is None or self.active_subject_id is None:
            return

        self._lesson_progress_flow.open_sequence_change(
            self.school_classes_by_id[self.active_school_class_id],
            self.active_subject_id,
        )

    def action_show_teaching_log(self) -> None:
        if self.active_school_class_id is None:
            return

        self.app.push_screen(
            TeachingLogScreen(
                self.active_school_class_id, subject_id=self.active_subject_id
            ),
        )

    @on(OptionList.OptionSelected, "#management-picker")
    @on(OptionList.OptionSelected, "#teaching-picker")
    def management_picker_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option_id
        if option_id is None:
            return

        match option_id:
            case "edit-assessments":
                self.app.push_screen(
                    EditAssessmentsScreen(), self.timetable_edit_finished
                )
            case "edit-classes":
                self.app.push_screen(EditClassesScreen(), self.classes_edited)
            case "curriculum":
                self.app.push_screen(CurriculumScreen())
            case "sequence-library":
                self.app.push_screen(
                    SequenceLibraryScreen(), self.sequence_library_closed
                )
            case "edit-timetable":
                self.app.push_screen(
                    EditTimetableScreen(), self.timetable_edit_finished
                )
            case "edit-closures":
                self.app.push_screen(
                    EditClosuresScreen(),
                    self.closures_edited,
                )
            case "distribution":
                self.app.push_screen(
                    DistributionScreen(
                        self.active_school_class_id, subject_id=self.active_subject_id
                    )
                )
            case "teaching-log":
                self.app.push_screen(TeachingLogScreen())
            case "settings":
                self.app.push_screen(SettingsScreen(), self.settings_changed)

    async def settings_changed(self, config: AppConfig | None) -> None:
        if config is None:
            # Der eigenständige Stundenzeitendialog kann bereits gespeichert haben.
            await self.refresh_current_view()
            return
        year_changed = config.active_school_year != self.app_config.active_school_year
        self.pult_app.app_config = config
        if year_changed:
            # Alle alten View-Daten und ausstehenden Navigationstimer verwerfen.
            if self._view_timer is not None:
                self._view_timer.stop()
            self.app.switch_screen(MainScreen())
        else:
            await self.refresh_current_view()
        self.notify("Einstellungen gespeichert.")

    def classes_edited(self, _: None) -> None:
        self.refresh_view_picker()

    async def timetable_edit_finished(self, _: None) -> None:
        await self.refresh_current_view()

    async def sequence_library_closed(self, _: None) -> None:
        await self.refresh_current_view()

    async def closures_edited(self, _: None) -> None:
        await self.refresh_current_view()
