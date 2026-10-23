"""Steuere Zusatztermine und die Folgesequenzauswahl beim Unterrichtsabschluss."""

from collections.abc import Awaitable, Callable

from pult.curriculum.sequence import Sequence
from pult.progress.class_progress import ClassProgress
from pult.progress.commands import (
    CompleteLessonResult,
    LessonCompletionState,
    ProgressCommandError,
    add_extra_lesson,
    complete_additional_lesson,
    set_active_sequence,
)
from pult.progress.queries import (
    get_available_next_sequences,
    get_next_lesson,
    get_suggested_next_sequence,
)
from pult.school.school_class import SchoolClass, load_school_classes
from pult.school.subject import load_subjects
from pult.screens.base_screen import PultScreen
from pult.screens.progress.add_extra_lesson_screen import (
    AddExtraLessonScreen,
    ExtraLessonFormResult,
)
from pult.screens.progress.select_next_sequence_screen import SelectNextSequenceScreen
from pult.services.progress import load_class_progress_data


class LessonProgressFlow:
    """Koordiniere Dialoge; der aufrufende Screen speichert und aktualisiert die Ansicht."""

    def __init__(
        self,
        screen: PultScreen[None],
        save_progress: Callable[
            [SchoolClass, ClassProgress, list[Sequence]], Awaitable[None]
        ],
    ) -> None:
        self.screen = screen
        self.save_progress = save_progress

    def open_extra_lesson(
        self,
        *,
        fixed_school_class_id: str | None = None,
        fixed_subject_id: str | None = None,
    ) -> None:
        """Öffne einen zusätzlichen Termin und verarbeite die bestätigten Eingaben."""
        config = self.screen.app_config
        try:
            school_classes = load_school_classes(
                config.root,
                config.active_school_year,
            )
            subjects = load_subjects(config.root)
        except (OSError, ValueError) as error:
            self.screen.notify(str(error), severity="error")
            return

        if not school_classes:
            self.screen.notify(
                "Für einen zusätzlichen Termin muss zuerst eine Klasse angelegt werden.",
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
                    config, school_class, sequences=self.screen.sequence_library
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
                        self.screen.notify(
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
                    await self.handle_result(
                        school_class,
                        lesson.title,
                        sequences,
                        result,
                        action_description="am zusätzlichen Termin abgeschlossen",
                    )
                    return

                updated_progress = add_extra_lesson(
                    progress,
                    form_result.subject_id,
                    form_result.date,
                    form_result.comment,
                )
                await self.save_progress(
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
                self.screen.notify(str(error), severity="error")
                return

            self.screen.notify(f"{school_class.id}: Zusätzlicher Termin eingetragen.")

        self.screen.app.push_screen(
            AddExtraLessonScreen(
                school_classes,
                subjects,
                fixed_school_class_id=fixed_school_class_id,
                fixed_subject_id=fixed_subject_id,
            ),
            extra_lesson_entered,
        )

    async def handle_result(
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
                    await self.save_progress(
                        school_class,
                        updated_progress,
                        sequences,
                    )
                except (OSError, ProgressCommandError, ValueError) as error:
                    self.screen.notify(str(error), severity="error")
                    return

                self.screen.notify(
                    f"{school_class.id}: '{lesson_title}' "
                    f"{action_description} und nächste Sequenz aktiviert."
                )

            self.screen.app.push_screen(
                SelectNextSequenceScreen(
                    available_sequences,
                    suggested_sequence.id,
                ),
                next_sequence_selected,
            )
            return

        try:
            await self.save_progress(
                school_class,
                result.progress,
                sequences,
            )
        except (OSError, ValueError) as error:
            self.screen.notify(str(error), severity="error")
            return

        if result.state is LessonCompletionState.COMPLETES_SUBJECT:
            self.screen.notify(
                f"{school_class.id}: '{lesson_title}' "
                f"{action_description}; "
                "das Fach ist vollständig abgeschlossen."
            )
        else:
            self.screen.notify(
                f"{school_class.id}: '{lesson_title}' {action_description}."
            )
