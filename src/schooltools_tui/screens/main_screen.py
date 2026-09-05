from dataclasses import dataclass
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Footer, Header, Label, OptionList

from schooltools_tui.curriculum.sequence import Sequence, load_sequence_library
from schooltools_tui.progress.class_progress import (
    ClassProgress,
    load_class_progress,
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
    get_next_lesson,
    get_next_planned_lesson,
    get_next_planned_lesson_for_class,
    get_suggested_next_sequence,
)
from schooltools_tui.school.period import load_periods
from schooltools_tui.school.school_class import SchoolClass, load_school_classes
from schooltools_tui.school.school_year import get_school_year_start
from schooltools_tui.school.subject import load_subjects
from schooltools_tui.school.timetable import get_timetable_path, load_timetable
from schooltools_tui.screens.base_screen import SchooltoolsScreen
from schooltools_tui.screens.add_extra_lesson_screen import (
    AddExtraLessonScreen,
    ExtraLessonFormResult,
)
from schooltools_tui.screens.cancel_lesson_screen import CancelLessonScreen
from schooltools_tui.screens.confirm_undo_screen import ConfirmUndoScreen
from schooltools_tui.screens.edit_classes_screen import EditClassesScreen
from schooltools_tui.screens.edit_timetable_screen import EditTimetableScreen
from schooltools_tui.screens.select_next_sequence_screen import (
    SelectNextSequenceScreen,
)
from schooltools_tui.screens.set_active_sequence_screen import (
    ActiveSequenceFormResult,
    SetActiveSequenceScreen,
)
from schooltools_tui.screens.sequence_library_screen import SequenceLibraryScreen
from schooltools_tui.views.home_view import HomeView
from schooltools_tui.views.school_class_view import SchoolClassView
from schooltools_tui.widgets.navigation import ManagementPicker, ViewPicker


@dataclass(frozen=True)
class PlannedLessonContext:
    school_class: SchoolClass
    progress: ClassProgress
    planned_lesson: PlannedLesson
    sequences: list[Sequence]


class MainScreen(SchooltoolsScreen[None]):
    BINDINGS: ClassVar = [
        ("n", "complete_next_lesson", "Stunde abschließen"),
        ("s", "skip_next_lesson", "Stunde überspringen"),
        ("c", "continue_next_lesson", "Lesson fortsetzen"),
        ("a", "cancel_next_lesson", "Ausfall eintragen"),
        ("p", "undo_last_entry", "Letzten Eintrag zurücknehmen"),
        ("z", "add_extra_lesson", "Zusatzunterricht"),
        ("w", "change_active_sequence", "Sequenz wechseln"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.school_classes_by_id: dict[str, SchoolClass] = {}
        self.active_school_class_id: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main"):
            with Vertical(id="navigation"):
                yield Label("ANSICHTEN", id="view-label")
                yield ViewPicker(id="view-picker")

                yield Label("VERWALTUNG", id="management-label")
                yield ManagementPicker(id="management-picker")

            with Container(id="content"):
                pass

        yield Footer()

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
            highlighted_option_id,
        )

    def refresh_school_classes(self) -> None:
        config = self.app_config
        school_classes = load_school_classes(config.root, config.active_school_year)
        self.school_classes_by_id = {
            school_class.id: school_class for school_class in school_classes
        }

    @on(OptionList.OptionHighlighted, "#view-picker")
    async def view_picker_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        option_id = event.option_id
        if option_id is None:
            return

        if option_id == "home":
            await self.show_home_view()
            return

        await self.show_school_class_view(
            self.school_classes_by_id[option_id.removeprefix("class-")]
        )

    async def switch_view(self, view: Widget) -> None:
        content = self.query_one("#content", Container)

        await content.remove_children()
        await content.mount(view)

    async def show_home_view(self) -> None:
        self.active_school_class_id = None
        self.refresh_bindings()
        config = self.app_config
        path = get_timetable_path(config.root, config.active_school_year)
        timetable_entries = load_timetable(path)
        periods = load_periods(config.root)
        subjects = load_subjects(config.root)
        await self.switch_view(HomeView(timetable_entries, subjects, periods))

    async def show_school_class_view(self, school_class: SchoolClass) -> None:
        self.active_school_class_id = school_class.id
        self.refresh_bindings()
        await self.switch_view(SchoolClassView(school_class))

    def check_action(
        self,
        action: str,
        parameters: tuple[object, ...],
    ) -> bool | None:
        if action in {"undo_last_entry", "change_active_sequence"}:
            return self.active_school_class_id is not None
        return super().check_action(action, parameters)

    async def refresh_current_view(self) -> None:
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
        config = self.app_config
        year = config.active_school_year

        try:
            school_classes = load_school_classes(config.root, year)
            self.school_classes_by_id = {
                school_class.id: school_class for school_class in school_classes
            }
            sequences = load_sequence_library(config.root)
            timetable_entries = load_timetable(
                get_timetable_path(config.root, year)
            )
            school_year_start = get_school_year_start(year)
            if self.active_school_class_id is None:
                progresses_by_class_id = {
                    school_class.id: load_class_progress(
                        config.root,
                        year,
                        school_class.id,
                    )
                    for school_class in school_classes
                }
                planned_lesson = get_next_planned_lesson(
                    progresses_by_class_id,
                    sequences,
                    timetable_entries,
                    school_classes,
                    school_year_start,
                )
                progress = (
                    progresses_by_class_id[planned_lesson.school_class_id]
                    if planned_lesson is not None
                    else None
                )
            else:
                school_class = self.school_classes_by_id[
                    self.active_school_class_id
                ]
                progress = load_class_progress(
                    config.root,
                    year,
                    school_class.id,
                )
                planned_lesson = get_next_planned_lesson_for_class(
                    progress,
                    sequences,
                    timetable_entries,
                    school_class,
                    school_year_start,
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

        school_class = self.school_classes_by_id[
            planned_lesson.school_class_id
        ]
        return PlannedLessonContext(
            school_class=school_class,
            progress=progress,
            planned_lesson=planned_lesson,
            sequences=sequences,
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

        self.app.push_screen(CancelLessonScreen(), cancellation_entered)

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
                sequences = load_sequence_library(config.root)
                progress = load_class_progress(
                    config.root,
                    config.active_school_year,
                    school_class.id,
                )

                if form_result.completes_next_lesson:
                    lesson = get_next_lesson(
                        progress,
                        sequences,
                        form_result.subject_id,
                        school_class.grade_level,
                    )
                    if lesson is None:
                        self.notify(
                            "Für dieses Fach gibt es keine offene Lesson.",
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
            ),
            extra_lesson_entered,
        )

    async def action_undo_last_entry(self) -> None:
        if self.active_school_class_id is None:
            return

        config = self.app_config
        school_class = self.school_classes_by_id[self.active_school_class_id]
        try:
            sequences = load_sequence_library(config.root)
            progress = load_class_progress(
                config.root,
                config.active_school_year,
                school_class.id,
            )
        except (OSError, KeyError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        if not progress.entries:
            self.notify(
                "Es gibt keinen Protokolleintrag zum Zurücknehmen.",
                severity="warning",
            )
            return

        async def undo_confirmed(confirmed: bool) -> None:
            if not confirmed:
                return

            try:
                updated_progress = undo_last_entry(progress)
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
            ConfirmUndoScreen(school_class.id),
            undo_confirmed,
        )

    def action_change_active_sequence(self) -> None:
        if self.active_school_class_id is None:
            return

        config = self.app_config
        school_class = self.school_classes_by_id[self.active_school_class_id]
        try:
            progress = load_class_progress(
                config.root,
                config.active_school_year,
                school_class.id,
            )
            sequences = load_sequence_library(config.root)
            subjects = load_subjects(config.root)
            has_available_sequence = any(
                get_available_next_sequences(
                    progress,
                    sequences,
                    subject_id,
                    school_class.grade_level,
                )
                for subject_id in school_class.subject_ids
            )
        except (OSError, KeyError, StopIteration, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        if not has_available_sequence:
            self.notify(
                "Für diese Klasse gibt es keine weitere offene Sequenz.",
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
            ),
            active_sequence_selected,
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
            self.notify(
                f"{school_class.id}: '{lesson_title}' "
                f"{action_description}."
            )

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

    def classes_edited(self, _: None) -> None:
        self.refresh_view_picker()

    async def timetable_edit_finished(self, _: None) -> None:
        if self.query(HomeView):
            await self.show_home_view()
