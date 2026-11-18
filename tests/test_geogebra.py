import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from pult.services.geogebra import GeoGebraOpenError, open_geogebra


def test_launch_passes_original_bytes_as_stdin_without_changing_file(
    tmp_path, monkeypatch, logging_session
):
    path = tmp_path / "Lineare Funktion ä $(echo test);.GGB"
    content = b"PK\x03\x04example-construction"
    path.write_bytes(content)
    before = path.stat().st_mtime_ns
    calls = []

    def launch(args, **kwargs):
        calls.append(args)
        assert args == [
            "/usr/bin/open",
            "-n",
            "-b",
            "org.geogebra.calculator.suite",
            "--stdin",
            str(path),
            "--args",
            "/dev/stdin",
        ]
        assert Path(args[5]).read_bytes() == content
        assert not kwargs.get("shell", False)
        assert kwargs["timeout"] > 0
        assert kwargs["stdout"] == kwargs["stderr"] == subprocess.DEVNULL
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr("pult.services.geogebra.subprocess.run", launch)
    open_geogebra(path)
    open_geogebra(path)
    assert len(calls) == 2  # Auch bei laufender Suite eine neue Instanz starten.
    assert path.read_bytes() == content
    assert path.stat().st_mtime_ns == before
    log = logging_session.path.read_text()
    assert log.count("geogebra_launch_succeeded") == 2
    assert str(path) not in log
    assert "example-construction" not in log


@pytest.mark.parametrize(
    ("error", "message", "reason"),
    [
        (None, "installiert", "launch_rejected"),
        (
            subprocess.TimeoutExpired("private-command", 15),
            "nicht rechtzeitig bestätigt",
            "timeout",
        ),
        (OSError("private-error"), "nicht gestartet", "launcher_failed"),
    ],
)
def test_launch_failures_have_actionable_messages_and_private_logs(
    tmp_path, monkeypatch, logging_session, error, message, reason
):
    path = tmp_path / "private-material.ggb"
    path.write_bytes(b"construction")
    launch = Mock(side_effect=error, return_value=subprocess.CompletedProcess([], 1))
    monkeypatch.setattr("pult.services.geogebra.subprocess.run", launch)
    with pytest.raises(GeoGebraOpenError, match=message):
        open_geogebra(path)
    log = logging_session.path.read_text()
    assert f"reason={reason}" in log
    assert "geogebra_launch_succeeded" not in log
    assert "private-" not in log


@pytest.mark.parametrize("unreadable", ["missing", "directory", "permission"])
def test_unreadable_file_does_not_start_app(tmp_path, monkeypatch, unreadable):
    path = tmp_path / "material.ggb"
    if unreadable == "directory":
        path.mkdir()
    elif unreadable == "permission":
        path.write_bytes(b"construction")
        original_open = Path.open

        def deny_material(self, *args, **kwargs):
            if self == path:
                raise PermissionError("No access")
            return original_open(self, *args, **kwargs)

        monkeypatch.setattr(Path, "open", deny_material)
    launch = Mock()
    monkeypatch.setattr("pult.services.geogebra.subprocess.run", launch)
    with pytest.raises(GeoGebraOpenError, match="nicht gelesen"):
        open_geogebra(path)
    launch.assert_not_called()
