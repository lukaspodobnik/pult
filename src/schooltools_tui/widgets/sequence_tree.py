from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from schooltools_tui.sequence import Sequence, sequence_sort_key
from schooltools_tui.subject import Subject


class SequenceTree(Tree[Sequence | None]):
    def __init__(self, *, id: str | None = None) -> None:
        super().__init__("Sequenzen", id=id)
        self.show_root = False

    def on_mount(self) -> None:
        self.root.expand()

    def populate(self, sequences: list[Sequence], subjects: list[Subject]) -> None:
        self.root.remove_children()

        subjects_by_id = {
            subject.id: subject
            for subject in subjects
        }
        unknown_subject_ids = {
            sequence.subject_id for sequence in sequences
        } - subjects_by_id.keys()
        if unknown_subject_ids:
            subject_ids = ", ".join(sorted(unknown_subject_ids))
            raise ValueError(f"Unbekannte Fach-IDs in der Sequenzbibliothek: {subject_ids}")

        sequences_by_subject: dict[str, list[Sequence]] = {}
        for sequence in sequences:
            sequences_by_subject.setdefault(sequence.subject_id, []).append(sequence)

        sorted_subjects = sorted(
            sequences_by_subject,
            key=lambda subject_id: subjects_by_id[subject_id].name.casefold(),
        )
        for subject_id in sorted_subjects:
            subject_node = self.root.add(subjects_by_id[subject_id].name)
            subject_sequences = sequences_by_subject[subject_id]
            grade_levels = sorted(
                {sequence.grade_level for sequence in subject_sequences}
            )

            for grade_level in grade_levels:
                grade_node = subject_node.add(
                    f"{grade_level}. Jahrgangsstufe",
                )
                grade_sequences = [
                    sequence
                    for sequence in subject_sequences
                    if sequence.grade_level == grade_level
                ]
                self._add_grade_sequences(grade_node, grade_sequences)

        self.root.expand()

    @staticmethod
    def _add_grade_sequences(
        grade_node: TreeNode[Sequence | None],
        sequences: list[Sequence],
    ) -> None:
        chapter_nodes: dict[str, TreeNode[Sequence | None]] = {}
        sorted_sequences = sorted(
            sequences,
            key=lambda sequence: (
                sequence_sort_key(sequence),
                sequence.title.casefold(),
            ),
        )

        for sequence in sorted_sequences:
            if sequence.chapter_id is None:
                grade_node.add(sequence.title, data=sequence)
                continue

            chapter_node = chapter_nodes.get(sequence.chapter_id)
            if chapter_node is None:
                assert sequence.chapter_title is not None
                chapter_node = grade_node.add(
                    sequence.chapter_title,
                    expand=True,
                )
                chapter_nodes[sequence.chapter_id] = chapter_node

            chapter_node.add(sequence.title, data=sequence)
