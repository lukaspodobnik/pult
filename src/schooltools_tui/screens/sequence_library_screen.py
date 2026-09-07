import shlex
import subprocess
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from schooltools_tui.curriculum.sequence import (
    Sequence,
    SequenceFileError,
    get_sequence_path,
    load_sequence,
)
from schooltools_tui.school.subject import load_subjects
from schooltools_tui.screens.base_screen import SchooltoolsScreen
from schooltools_tui.widgets.footer import SchooltoolsFooter
from schooltools_tui.widgets.sequence_preview import SequencePreview
from schooltools_tui.widgets.sequence_tree import SequenceTree


class SequenceLibraryScreen(SchooltoolsScreen[None]):
    BINDINGS: ClassVar = [("escape", "close", "Zurück")]

    def compose(self) -> ComposeResult:
        with Horizontal(id="sequence-library"):
            with Vertical(id="sequence-navigation"):
                yield SequenceTree(id="sequence-tree")

            with Container(id="sequence-content"):
                yield SequencePreview(id="sequence-preview")

        yield SchooltoolsFooter()

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

    @on(Tree.NodeHighlighted, "#sequence-tree")
    def sequence_highlighted(self, event: Tree.NodeHighlighted) -> None:
        sequence = event.node.data

        if sequence is None:
            return

        preview = self.query_one("#sequence-preview", SequencePreview)
        preview.show_sequence(sequence)

    @on(Tree.NodeSelected, "#sequence-tree")
    def sequence_selected(self, event: Tree.NodeSelected) -> None:
        self.open_sequence_in_editor(event.node)

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
        self.schooltools_app.require_sequence_library().invalidate()

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
