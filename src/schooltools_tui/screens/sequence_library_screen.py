import shlex
import subprocess
from typing import ClassVar
from textual.widgets.tree import TreeNode
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Label, Tree

from schooltools_tui.screens.base_screen import SchooltoolsScreen
from schooltools_tui.sequence import Sequence, get_sequence_path, load_sequence, load_sequence_library
from schooltools_tui.subject import load_subjects
from schooltools_tui.widgets.sequence_preview import SequencePreview
from schooltools_tui.widgets.sequence_tree import SequenceTree


class SequenceLibraryScreen(SchooltoolsScreen[None]):
    BINDINGS: ClassVar = [("escape", "close", "Zurück")]

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="sequence-library"):
            with Vertical(id="sequence-navigation"):
                yield Label("SEQUENZBIBLIOTHEK", id="sequence-navigation-title")
                yield SequenceTree(id="sequence-tree")

            with Container(id="sequence-content"):
                yield SequencePreview(id="sequence-preview")

        yield Footer()

    def on_mount(self) -> None:
        config = self.app_config
        sequences = load_sequence_library(config.root)
        subjects = load_subjects(config.root)

        tree = self.query_one("#sequence-tree", SequenceTree)
        tree.populate(sequences, subjects)

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
        sequence = node.data
        if sequence is None:
            return

        config = self.app_config

        command = [
            *shlex.split(config.editor),
            get_sequence_path(
                config.root, sequence.grade_level, sequence.subject_id, sequence.id
            ),
        ]

        with self.app.suspend():
            subprocess.run(command, check=False)

        updated_sequence = load_sequence(
            config.root, sequence.grade_level, sequence.subject_id, sequence.id
        )

        node.data = updated_sequence

        preview = self.query_one("#sequence-preview", SequencePreview)
        preview.show_sequence(updated_sequence)
