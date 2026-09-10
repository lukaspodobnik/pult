import shlex
import shutil
import subprocess
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets.tree import TreeNode

from pult.curriculum.sequence import (
    Sequence,
    SequenceFileError,
    get_sequence_path,
    load_sequence,
)
from pult.school.subject import load_subjects
from pult.screens.base_screen import PultScreen
from pult.screens.lesson_screen import LessonScreen
from pult.screens.task_screen import TaskScreen
from pult.widgets.footer import PultFooter
from pult.widgets.scrolling import Horizontal, OptionList, Tree, Vertical
from pult.widgets.sequence_preview import SequencePreview
from pult.widgets.sequence_tree import SequenceTree


class SequenceLibraryScreen(PultScreen[None]):
    BINDINGS: ClassVar = [
        ("escape", "close", "Zurück"),
        ("e", "edit_sequence", "Bearbeiten"),
        ("a", "open_tasks", "Aufgaben"),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal(id="sequence-library"):
            with Vertical(id="sequence-navigation"):
                yield SequenceTree(id="sequence-tree")

            with Container(id="sequence-content"):
                yield SequencePreview(id="sequence-preview")

        yield PultFooter()

    def on_mount(self) -> None:
        config = self.app_config
        sequences = self.sequence_library
        subjects = load_subjects(config.root)

        tree = self.query_one("#sequence-tree", SequenceTree)
        tree.populate(sequences, subjects)
        tree.focus()
        tree.move_cursor(tree.root.children[0] if tree.root.children else None)

    def action_close(self) -> None:
        self.dismiss()

    def action_open_tasks(self) -> None:
        tree = self.query_one(SequenceTree)
        preview = self.query_one(SequencePreview)
        sequence = (
            tree.cursor_node.data
            if tree.has_focus and tree.cursor_node
            else preview.sequence
        )
        if sequence is None:
            return
        try:
            screen = TaskScreen(
                sequence,
                get_sequence_path(
                    self.app_config.root,
                    sequence.grade_level,
                    sequence.subject_id,
                    sequence.id,
                ).parent,
            )
        except (OSError, ValueError) as error:
            self.notify(str(error), severity="error")
            return
        focused = self.focused

        def closed(updated: Sequence | None):
            self.lesson_closed(updated)
            if focused is not None:
                focused.focus()

        self.app.push_screen(screen, closed)

    @on(Tree.NodeHighlighted, "#sequence-tree")
    def sequence_highlighted(self, event: Tree.NodeHighlighted) -> None:
        sequence = event.node.data

        if sequence is None:
            return

        preview = self.query_one("#sequence-preview", SequencePreview)
        preview.show_sequence(sequence)

    @on(OptionList.OptionSelected, "#sequence-preview")
    def open_lesson(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        preview = self.query_one(SequencePreview)
        if preview.sequence is None or preview.selected_lesson is None:
            return
        self.app.push_screen(
            LessonScreen(preview.sequence, preview.selected_lesson.id),
            self.lesson_closed,
        )

    def lesson_closed(self, updated: Sequence | None) -> None:
        if updated is None:
            return
        tree = self.query_one(SequenceTree)

        def update_node(node):
            if node.data is not None and (
                node.data.grade_level,
                node.data.subject_id,
                node.data.id,
            ) == (updated.grade_level, updated.subject_id, updated.id):
                node.data = updated
                node.set_label(updated.title)
            for child in node.children:
                update_node(child)

        update_node(tree.root)
        preview = self.query_one(SequencePreview)
        preview.show_sequence(updated)
        preview.focus()

    def action_edit_sequence(self) -> None:
        node = self.query_one("#sequence-tree", SequenceTree).cursor_node
        if node is not None:
            self.open_sequence_in_editor(node)

    def open_sequence_in_editor(self, node: TreeNode[Sequence | None]) -> None:
        """Öffne eine Sequenz im konfigurierten Editor und lade sie danach neu."""
        sequence = node.data
        if sequence is None:
            return

        config = self.app_config

        path = get_sequence_path(
            config.root,
            sequence.grade_level,
            sequence.subject_id,
            sequence.id,
        )
        try:
            command = [*shlex.split(config.editor), str(path)]
        except ValueError as error:
            self.notify(
                f"Der konfigurierte Editor-Befehl ist ungültig: {error}",
                severity="error",
            )
            return

        if not command or len(command) < 2 or shutil.which(command[0]) is None:
            self.notify(
                "Der gewählte Editor ist nicht installiert oder nicht im Suchpfad. "
                "Installiere ihn oder wähle unter Einstellungen einen anderen Editor.",
                severity="warning",
            )
            return

        try:
            with self.app.suspend():
                result = subprocess.run(command, check=False)
        except OSError as error:
            self.notify(
                f"Der Editor konnte nicht gestartet werden: {error}",
                severity="error",
            )
            return

        # Auch bei ungültigen Änderungen dürfen spätere Aufrufe keine alten Daten nutzen.
        self.pult_app.require_sequence_library().invalidate()

        if result.returncode != 0:
            self.notify(
                f"Der Editor wurde mit Status {result.returncode} beendet.",
                severity="warning",
            )

        try:
            updated_sequence = load_sequence(
                config.root,
                sequence.grade_level,
                sequence.subject_id,
                sequence.id,
            )
        except SequenceFileError as error:
            self.notify(str(error), severity="error", timeout=10)
            return
        except OSError as error:
            self.notify(
                f"Die Sequenzdatei konnte nicht gelesen werden: {error}",
                severity="error",
            )
            return

        node.data = updated_sequence
        node.set_label(updated_sequence.title)

        preview = self.query_one("#sequence-preview", SequencePreview)
        preview.show_sequence(updated_sequence)
