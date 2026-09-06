from pathlib import Path

from schooltools_tui.curriculum.sequence import Sequence, load_sequence_library


class SequenceLibrary:
    """Halte die Bibliothek einer Datenablage bis zur nächsten Invalidierung bereit."""

    def __init__(self, root: Path) -> None:
        self.root: Path = root
        self._sequences: list[Sequence] | None = None

    def get_sequences(self) -> list[Sequence]:
        """Lade bei Bedarf; Aufrufer behandeln die zurückgegebenen Daten als lesend."""
        if self._sequences is None:
            self._sequences = load_sequence_library(self.root)

        return self._sequences

    def invalidate(self) -> None:
        """Verwerfe den Speicherstand, damit der nächste Zugriff neu von Dateien lädt."""
        self._sequences = None
