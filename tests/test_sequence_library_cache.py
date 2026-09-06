from unittest.mock import Mock

import pytest

from schooltools_tui.app import SchooltoolsApp
from schooltools_tui.config import AppConfig
from schooltools_tui.services.sequence_library import SequenceLibrary


@pytest.mark.parametrize("empty", [False, True])
def test_library_loads_once_and_reloads_after_invalidation(
    tmp_path, monkeypatch, sequences, empty
):
    loaded = [] if empty else sequences
    loader = Mock(return_value=loaded)
    monkeypatch.setattr(
        "schooltools_tui.services.sequence_library.load_sequence_library", loader
    )
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
    monkeypatch.setattr(
        "schooltools_tui.services.sequence_library.load_sequence_library", loader
    )
    library = SequenceLibrary(tmp_path)
    with pytest.raises(ValueError):
        library.get_sequences()
    assert library.get_sequences() is sequences


@pytest.mark.parametrize("after_setup", [False, True])
def test_app_initializes_and_shares_library(tmp_path, monkeypatch, after_setup):
    app = SchooltoolsApp()
    monkeypatch.setattr(app, "push_screen", Mock())
    config = AppConfig(tmp_path, "true", "2026-2027")
    with pytest.raises(RuntimeError):
        app.require_sequence_library()
    if after_setup:
        app.on_setup_complete(config)
    else:
        app.app_config = config
        app.show_initial_screen()
    library = app.require_sequence_library()
    assert library.root == tmp_path
    app.show_initial_screen()
    assert app.require_sequence_library() is library
    app.app_config = AppConfig(tmp_path / "other", "true", "2026-2027")
    app.show_initial_screen()
    assert app.require_sequence_library() is not library
