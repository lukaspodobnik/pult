from unittest.mock import Mock

import pytest

from pult.services.sequence_library import SequenceLibrary


@pytest.mark.parametrize("empty", [False, True])
def test_library_loads_once_and_reloads_after_invalidation(
    tmp_path, monkeypatch, sequences, empty
):
    loaded = [] if empty else sequences
    loader = Mock(return_value=loaded)
    monkeypatch.setattr("pult.services.sequence_library.load_sequence_library", loader)
    library = SequenceLibrary(tmp_path)
    loader.assert_not_called()
    assert library.get_sequences() is loaded
    assert library.get_sequences() is loaded
    loader.assert_called_once_with(tmp_path)
    library.invalidate()
    assert library.get_sequences() is loaded
    assert loader.call_count == 2


def test_failed_loading_can_be_retried(tmp_path, monkeypatch, sequences):
    loader = Mock(side_effect=[ValueError("Ungültige Datei"), sequences])
    monkeypatch.setattr("pult.services.sequence_library.load_sequence_library", loader)
    library = SequenceLibrary(tmp_path)
    with pytest.raises(ValueError):
        library.get_sequences()
    assert library.get_sequences() is sequences
