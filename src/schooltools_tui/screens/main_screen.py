from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar
from zoneinfo import ZoneInfo

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import DescendantFocus
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import ContentSwitcher, OptionList, Static

from schooltools_tui.curriculum.sequence import Sequence
from schooltools_tui.progress.class_progress import (
    ClassProgress,
    save_class_progress,
    validate_class_progress,
)
from schooltools_tui.progress.commands import (
    CompleteLessonResult,
    LessonCompletionState,
    ProgressCommandError,
    add_extra_lesson,
    cancel_scheduled_lesson,
    complete_additional_lesson,
    complete_lesson,
    continue_lesson,
    set_active_sequence,
    skip_lesson,
    undo_last_entry,
)
from schooltools_tui.progress.queries import (
    PlannedLesson,
    get_available_next_sequences,
    get_class_progress_summary,
    get_home_dashboard_summary,
    get_next_lesson,
    get_next_planned_lesson,
    get_next_planned_lessons_for_class,
    get_suggested_next_sequence,
)
from schooltools_tui.school.period import load_periods
from schooltools_tui.school.school_class import SchoolClass, load_school_classes
from schooltools_tui.school.subject import load_subjects
from schooltools_tui.screens.add_extra_lesson_screen import (
    AddExtraLessonScreen,
    ExtraLessonFormResult,
)
from schooltools_tui.screens.base_screen import SchooltoolsScreen
from schooltools_tui.screens.cancel_lesson_screen import CancelLessonScreen
from schooltools_tui.screens.confirm_undo_screen import ConfirmUndoScreen
from schooltools_tui.screens.edit_classes_screen import EditClassesScreen
from schooltools_tui.screens.edit_closures_screen import EditClosuresScreen
from schooltools_tui.screens.edit_timetable_screen import EditTimetableScreen
from schooltools_tui.screens.select_next_sequence_screen import (
    SelectNextSequenceScreen,
)
from schooltools_tui.screens.sequence_library_screen import SequenceLibraryScreen
from schooltools_tui.screens.set_active_sequence_screen import (
    ActiveSequenceFormResult,
    SetActiveSequenceScreen,
)
from schooltools_tui.screens.teaching_log_screen import TeachingLogScreen
from schooltools_tui.services.progress import (
    load_class_progress_data,
    load_planning_data,
)
from schooltools_tui.views.home_view import HomeView
from schooltools_tui.views.school_class_view import SchoolClassView
from schooltools_tui.widgets.dashboard.timetable import TimetablePanel
from schooltools_tui.widgets.footer import SchooltoolsFooter
from schooltools_tui.widgets.navigation import ManagementPicker, ViewPicker


@dataclass(frozen=True)
class PlannedLessonContext:
    school_class: SchoolClass
    progress: ClassProgress
    planned_lesson: PlannedLesson
    sequences: list[Sequence]


class MainScreen(SchooltoolsScreen[None]):
    VIEW_DEBOUNCE_SECONDS: ClassVar[float] = 0.06
    BINDINGS: ClassVar = [
        ("n", "complete_next_lesson", "Abschließen"),
        ("s", "skip_next_lesson", "Überspringen"),
        ("c", "continue_next_lesson", "Fortsetzen"),
        ("a", "cancel_next_lesson", "Ausfall"),
        ("z", "add_extra_lesson", "Zusatzunterricht"),
        ("p", "undo_last_entry", "Rückgängig"),
        ("l", "show_teaching_log", "Protokoll"),
        ("w", "change_active_sequence", "Sequenz wechseln"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.school_classes_by_id: dict[str, SchoolClass] = {}
        self.active_school_class_id: str | None = None
        self.active_subject_id: str | None = None
        self._pending_view_id: str | None = None
        self._view_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="navigation"):
                yield Static("SCHOOLTOOLS\nLogo-Platzhalter", id="logo-placeholder")
                yield ViewPicker(id="view-picker")
                yield ManagementPicker(id="management-picker")

            content = ContentSwitcher(id="content")
            content.can_focus_children = False
            yield content

        yield SchooltoolsFooter()

    def on_mount(self) -> None:
        self.refresh_view_picker()
        self.query_one("#view-picker", ViewPicker).focus()

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
        content = self.query_one("#content", ContentSwitcher)
        if not view.is_mounted:
            await content.add_content(view, id=type(view).__name__)
        content.current = view.id

    async def show_home_view(self) -> None:
        """Lade alle Dashboarddaten neu und zeige anschließend die HomeView."""
        self.active_school_class_id = None
        self.active_subject_id = None
        config = self.app_config
        try:
            data = load_planning_data(config, sequences=self.sequence_library)
            periods = load_periods(config.root)
            subjects = load_subjects(config.root)
            dashboard = get_home_dashboard_summary(
                datetime.now(ZoneInfo("Europe/Berlin")),
                data.progresses_by_class_id,
                data.sequences,
                data.timetable_entries,
                periods,
                data.school_classes,
                data.school_calendar,
                data.school_closures,
                data.class_closures_by_class_id,
            )
        except (OSError, KeyError, StopIteration, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        self.school_classes_by_id = {
            school_class.id: school_class for school_class in data.school_classes
        }
        views = self.query(HomeView)
        if views:
            view = views.first()
            await view.update_data(
                data.timetable_entries,
                subjects,
                periods,
                data.sequences,
                dashboard,
            )
        else:
            view = HomeView(
                data.timetable_entries, subjects, periods, data.sequences, dashboard
            )
        await self.switch_view(view)
        # Gleiche Rahmenhöhen, auch wenn die Anzahl der Stunden geändert wird.
        self.query_one(ViewPicker).styles.height = view.query_one(
            TimetablePanel
        ).styles.height
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
            data = load_planning_data(
                config, school_class.id, sequences=self.sequence_library
            )
            school_class = data.school_classes[0]
            if subject_id is None:
                subject_id = (
                    self.active_subject_id
                    if self.active_school_class_id == school_class.id
                    and self.active_subject_id in school_class.subject_ids
                    else school_class.subject_ids[0]
                )
            if subject_id not in school_class.subject_ids:
                raise ValueError("Das ausgewählte Fach gehört nicht zu dieser Klasse.")
            subjects = load_subjects(config.root)
            progress_summaries = get_class_progress_summary(
                data.progresses_by_class_id[school_class.id],
                data.sequences,
                data.timetable_entries,
                school_class,
                data.school_calendar,
                data.school_closures,
                data.class_closures_by_class_id[school_class.id],
            )
        except (OSError, KeyError, StopIteration, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        progress_summaries = tuple(
            summary
            for summary in progress_summaries
            if summary.subject_id == subject_id
        )
        self.active_school_class_id = school_class.id
        self.active_subject_id = subject_id
        views = self.query(SchoolClassView)
        if views:
            view = views.first()
            await view.update_data(school_class, subjects, progress_summaries)
        else:
            view = SchoolClassView(school_class, subjects, progress_summaries)
        await self.switch_view(view)
        view.query_one(".class-next-lesson").styles.height = self.query_one(
            ViewPicker
        ).styles.height
        if self._pending_view_id is None:
            self.refresh_bindings()

    def check_action(
        self,
        action: str,
        parameters: tuple[object, ...],
    ) -> bool | None:
        if isinstance(self.app.focused, ManagementPicker) and action in {
            "complete_next_lesson",
            "skip_next_lesson",
            "continue_next_lesson",
            "cancel_next_lesson",
            "add_extra_lesson",
            "undo_last_entry",
            "change_active_sequence",
        }:
            return False
        if self._pending_view_id is not None and any(
            (binding[1] if isinstance(binding, tuple) else binding.action) == action
            for binding in self.BINDINGS
        ):
            # Während Highlight und Ansicht auseinanderliegen, keine falsche Klasse ändern.
            return None
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
        config = self.app_config
        validate_class_progress(progress, school_class, sequences)
        save_class_progress(
            config.root,
            config.active_school_year,
            school_class.id,
            progress,
        )
        await self.refresh_current_view()

    def load_planned_lesson_context(self) -> PlannedLessonContext | None:
        """Lade den Kontext für die nächste globale oder klassenbezogene Lesson."""
        config = self.app_config

        try:
            data = load_planning_data(
                config, self.active_school_class_id, sequences=self.sequence_library
            )
            self.school_classes_by_id.update(
                {school_class.id: school_class for school_class in data.school_classes}
            )
            if self.active_school_class_id is None:
                planned_lesson = get_next_planned_lesson(
                    data.progresses_by_class_id,
                    data.sequences,
                    data.timetable_entries,
                    data.school_classes,
                    data.school_calendar,
                    data.school_closures,
                    data.class_closures_by_class_id,
                )
            else:
                class_id = self.active_school_class_id
                planned_lesson = next(
                    (
                        lesson
                        for lesson in get_next_planned_lessons_for_class(
                            data.progresses_by_class_id[class_id],
                            data.sequences,
                            data.timetable_entries,
                            self.school_classes_by_id[class_id],
                            data.school_calendar,
                            data.school_closures,
                            data.class_closures_by_class_id[class_id],
                        )
                        if lesson.subject_id == self.active_subject_id
                    ),
                    None,
                )
            progress = (
                data.progresses_by_class_id[planned_lesson.school_class_id]
                if planned_lesson is not None
                else None
            )
        except (OSError, KeyError, ValueError) as error:
            self.notify(str(error), severity="error")
            return None

        if planned_lesson is None or progress is None:
            self.notify(
                "Es gibt keine offene geplante Stunde.",
                severity="warning",
            )
            return None

        school_class = self.school_classes_by_id[planned_lesson.school_class_id]
        return PlannedLessonContext(
            school_class=school_class,
            progress=progress,
            planned_lesson=planned_lesson,
            sequences=data.sequences,
        )

    async def action_complete_next_lesson(self) -> None:
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

        await self.handle_lesson_progress_result(
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

        await self.handle_lesson_progress_result(
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
            f"'{context.planned_lesson.lesson.title}' wird fortgesetzt."
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
                f"'{context.planned_lesson.lesson.title}' eingetragen."
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

    def action_add_extra_lesson(self) -> None:
        config = self.app_config
        try:
            school_classes = load_school_classes(
                config.root,
                config.active_school_year,
            )
            subjects = load_subjects(config.root)
        except (OSError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        if not school_classes:
            self.notify(
                "Für Zusatzunterricht muss zuerst eine Klasse angelegt werden.",
                severity="warning",
            )
            return

        school_classes_by_id = {
            school_class.id: school_class for school_class in school_classes
        }

        async def extra_lesson_entered(
            form_result: ExtraLessonFormResult | None,
        ) -> None:
            if form_result is None:
                return

            try:
                school_class = school_classes_by_id[form_result.school_class_id]
                data = load_class_progress_data(
                    config, school_class, sequences=self.sequence_library
                )
                sequences, progress = data.sequences, data.progress

                if form_result.completes_next_lesson:
                    lesson = get_next_lesson(
                        progress,
                        sequences,
                        form_result.subject_id,
                        school_class.grade_level,
                    )
                    if lesson is None:
                        self.notify(
                            "Für dieses Fach gibt es keine offene geplante Stunde.",
                            severity="warning",
                        )
                        return

                    result = complete_additional_lesson(
                        progress,
                        form_result.subject_id,
                        school_class.grade_level,
                        form_result.date,
                        sequences,
                        form_result.comment,
                    )
                    await self.handle_lesson_progress_result(
                        school_class,
                        lesson.title,
                        sequences,
                        result,
                        action_description="im Zusatzunterricht abgeschlossen",
                    )
                    return

                updated_progress = add_extra_lesson(
                    progress,
                    form_result.subject_id,
                    form_result.date,
                    form_result.comment,
                )
                await self.save_progress_and_refresh(
                    school_class,
                    updated_progress,
                    sequences,
                )
            except (
                OSError,
                KeyError,
                ProgressCommandError,
                StopIteration,
                ValueError,
            ) as error:
                self.notify(str(error), severity="error")
                return

            self.notify(f"{school_class.id}: Zusatzunterricht eingetragen.")

        self.app.push_screen(
            AddExtraLessonScreen(
                school_classes,
                subjects,
                fixed_school_class_id=self.active_school_class_id,
                fixed_subject_id=self.active_subject_id,
            ),
            extra_lesson_entered,
        )

    async def action_undo_last_entry(self) -> None:
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

        selected_subject_id = self.active_subject_id
        config = self.app_config
        school_class = self.school_classes_by_id[self.active_school_class_id]
        try:
            data = load_class_progress_data(
                config, school_class, sequences=self.sequence_library
            )
            sequences, progress = data.sequences, data.progress
            subjects = load_subjects(config.root)
            has_available_sequence = bool(
                get_available_next_sequences(
                    progress, sequences, selected_subject_id, school_class.grade_level
                )
            )
        except (OSError, KeyError, StopIteration, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        if not has_available_sequence:
            self.notify(
                "Für dieses Fach gibt es keine weitere offene Sequenz.",
                severity="warning",
            )
            return

        subjects_by_id = {subject.id: subject for subject in subjects}

        async def active_sequence_selected(
            form_result: ActiveSequenceFormResult | None,
        ) -> None:
            if form_result is None:
                return

            try:
                updated_progress = set_active_sequence(
                    progress,
                    form_result.subject_id,
                    form_result.sequence_id,
                    school_class.grade_level,
                    sequences,
                )
                await self.save_progress_and_refresh(
                    school_class,
                    updated_progress,
                    sequences,
                )
            except (OSError, ProgressCommandError, ValueError) as error:
                self.notify(str(error), severity="error")
                return

            self.notify(
                f"{school_class.id}: Aktive Sequenz für "
                f"'{subjects_by_id[form_result.subject_id].name}' gewechselt."
            )

        self.app.push_screen(
            SetActiveSequenceScreen(
                school_class,
                progress,
                sequences,
                subjects,
                fixed_subject_id=selected_subject_id,
            ),
            active_sequence_selected,
        )

    def action_show_teaching_log(self) -> None:
        if self.active_school_class_id is None:
            return

        self.app.push_screen(
            TeachingLogScreen(
                self.active_school_class_id, subject_id=self.active_subject_id
            ),
        )

    async def handle_lesson_progress_result(
        self,
        school_class: SchoolClass,
        lesson_title: str,
        sequences: list[Sequence],
        result: CompleteLessonResult,
        *,
        action_description: str,
    ) -> None:
        """Speichere ein Command-Ergebnis oder fordere zuerst eine Folgesequenz an."""
        if result.state is LessonCompletionState.NEEDS_NEXT_SEQUENCE:
            available_sequences = get_available_next_sequences(
                result.progress,
                sequences,
                result.subject_id,
                school_class.grade_level,
            )
            suggested_sequence = get_suggested_next_sequence(
                result.progress,
                sequences,
                result.subject_id,
                school_class.grade_level,
            )
            assert suggested_sequence is not None

            async def next_sequence_selected(sequence_id: str | None) -> None:
                if sequence_id is None:
                    return

                try:
                    updated_progress = set_active_sequence(
                        result.progress,
                        result.subject_id,
                        sequence_id,
                        school_class.grade_level,
                        sequences,
                    )
                    await self.save_progress_and_refresh(
                        school_class,
                        updated_progress,
                        sequences,
                    )
                except (OSError, ProgressCommandError, ValueError) as error:
                    self.notify(str(error), severity="error")
                    return

                self.notify(
                    f"{school_class.id}: '{lesson_title}' "
                    f"{action_description} und nächste Sequenz aktiviert."
                )

            self.app.push_screen(
                SelectNextSequenceScreen(
                    available_sequences,
                    suggested_sequence.id,
                ),
                next_sequence_selected,
            )
            return

        try:
            await self.save_progress_and_refresh(
                school_class,
                result.progress,
                sequences,
            )
        except (OSError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        if result.state is LessonCompletionState.COMPLETES_SUBJECT:
            self.notify(
                f"{school_class.id}: '{lesson_title}' "
                f"{action_description}; "
                "das Fach ist vollständig abgeschlossen."
            )
        else:
            self.notify(f"{school_class.id}: '{lesson_title}' {action_description}.")

    @on(OptionList.OptionSelected, "#management-picker")
    def management_picker_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option_id
        if option_id is None:
            return

        match option_id:
            case "edit-classes":
                self.app.push_screen(EditClassesScreen(), self.classes_edited)
            case "sequence-library":
                self.app.push_screen(SequenceLibraryScreen())
            case "edit-timetable":
                self.app.push_screen(
                    EditTimetableScreen(), self.timetable_edit_finished
                )
            case "edit-closures":
                self.app.push_screen(
                    EditClosuresScreen(),
                    self.closures_edited,
                )
            case "teaching-log":
                self.app.push_screen(TeachingLogScreen())

    def classes_edited(self, _: None) -> None:
        self.refresh_view_picker()

    async def timetable_edit_finished(self, _: None) -> None:
        await self.refresh_current_view()

    async def closures_edited(self, _: None) -> None:
        await self.refresh_current_view()
