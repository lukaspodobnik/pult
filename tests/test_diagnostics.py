import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from pult import main
from pult.services import diagnostics


@pytest.mark.parametrize("debug", [False, True])
def test_levels_reconfiguration_and_no_console_output(tmp_path, capsys, debug):
    first = diagnostics.configure_logging(directory=tmp_path, debug=debug)
    try:
        second = diagnostics.configure_logging(directory=tmp_path, debug=debug)
        assert first.closed
        logger = logging.getLogger("pult.test")
        logger.info("one_information")
        logger.debug("one_detail")
        second.close()
        text = second.path.read_text()
        assert text.count("one_information") == 1
        assert ("one_detail" in text) is debug
        assert "session=" in text and "request=-" in text
        assert "session_stopped" in text
        assert capsys.readouterr() == ("", "")
    finally:
        diagnostics._session.close()


def test_rotation_retains_only_three_backups(logging_session, monkeypatch):
    handler = logging_session.handler
    monkeypatch.setattr(handler, "maxBytes", 350)
    for index in range(30):
        logging.getLogger("pult.test").info("entry=%02d %s", index, "x" * 80)
    files = sorted(logging_session.path.parent.glob("pult.log*"))
    assert [p.name for p in files] == [
        "pult.log",
        "pult.log.1",
        "pult.log.2",
        "pult.log.3",
    ]
    assert "entry=29" in files[0].read_text()
    assert "entry=00" not in "".join(p.read_text() for p in files)


def test_unavailable_directory_does_not_break_logging(tmp_path, capsys):
    target = tmp_path / "not-a-directory"
    target.write_text("keep")
    session = diagnostics.configure_logging(directory=target / "logs")
    try:
        assert session.failed
        logging.getLogger("pult.test").error("cannot write")
        assert target.read_text() == "keep"
        assert capsys.readouterr() == ("", "")
    finally:
        session.close()


def test_later_rotation_failure_does_not_print_or_raise(
    logging_session, monkeypatch, capsys
):
    def failure():
        raise OSError("disk unavailable")

    monkeypatch.setattr(logging_session.handler, "maxBytes", 1)
    monkeypatch.setattr(logging_session.handler, "doRollover", failure)
    logging.getLogger("pult.test").error("rotation failed")
    logging.getLogger("pult.test").error("later entry")
    assert logging_session.failed
    assert capsys.readouterr() == ("", "")


def test_exception_chain_has_locations_without_user_content(logging_session):
    logger = logging.getLogger("pult.test")
    try:
        try:
            raise ValueError("PRIVATE_DOCUMENT_TEXT")
        except ValueError as error:
            raise RuntimeError("PRIVATE_INPUT") from error
    except RuntimeError as error:
        diagnostics.log_failure(logger, "operation_failed", error)
        diagnostics.log_failure(logger, "duplicate_failure", error)
    text = logging_session.path.read_text()
    assert "ValueError" in text and "RuntimeError" in text
    assert "Caused by:" in text
    assert "test_diagnostics.py:" in text
    assert "PRIVATE_" not in text
    assert "duplicate_failure" not in text


def test_concurrent_operations_keep_separate_context(logging_session):
    async def task():
        with diagnostics.operation("render") as request:
            logging.getLogger("pult.test").debug("started id=%s", request)
            await asyncio.sleep(0)
            logging.getLogger("pult.test").debug("finished id=%s", request)
            return request

    async def run():
        return await asyncio.gather(task(), task())

    requests = asyncio.run(run())
    assert len(set(requests)) == 2
    lines = logging_session.path.read_text().splitlines()
    for request in requests:
        matching = [line for line in lines if f"request={request} " in line]
        assert len(matching) == 2
        assert all(f"id={request}" in line for line in matching)
    logging.getLogger("pult.test").debug("outside")
    assert "request=- outside" in logging_session.path.read_text()


def test_async_failure_and_expected_cancellation(logging_session):
    async def run():
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(diagnostics.log_async_exception)
        try:
            raise RuntimeError("PRIVATE_ASYNC_INPUT")
        except RuntimeError as error:
            loop.call_exception_handler(
                {"exception": error, "message": "PRIVATE_CONTEXT"}
            )
        loop.call_exception_handler({"exception": asyncio.CancelledError()})

    asyncio.run(run())
    text = logging_session.path.read_text()
    assert text.count("async_task_failed") == 1
    assert "DEBUG pult.asyncio" in text and "async_task_cancelled" in text
    assert "PRIVATE_" not in text


@pytest.mark.parametrize(
    ("platform", "xdg", "relative"),
    [
        ("darwin", "/somewhere", "Library/Logs/PULT"),
        ("linux", "relative", ".local/state/pult/logs"),
        ("linux", "", ".local/state/pult/logs"),
    ],
)
def test_default_log_directory(monkeypatch, tmp_path, platform, xdg, relative):
    monkeypatch.setattr(diagnostics.sys, "platform", platform)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("XDG_STATE_HOME", xdg)
    assert diagnostics.log_directory() == tmp_path / relative


def test_absolute_xdg_state_home(monkeypatch, tmp_path):
    monkeypatch.setattr(diagnostics.sys, "platform", "linux")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert diagnostics.log_directory() == tmp_path / "pult/logs"


def test_help_does_not_start_graphics_or_create_logs(tmp_path, monkeypatch, capsys):
    from pult.services.documents import material_rendering

    monkeypatch.setattr(diagnostics, "log_directory", lambda: tmp_path / "logs")

    def forbidden():
        pytest.fail("Help must not probe terminal graphics")

    monkeypatch.setattr(material_rendering, "initialize_graphics", forbidden)
    with pytest.raises(SystemExit) as result:
        main(["--help"])
    assert result.value.code == 0
    assert not (tmp_path / "logs").exists()
    output = capsys.readouterr()
    assert "--debug" in output.out
    assert str(tmp_path / "logs/pult.log") in output.out
    assert not output.err


@pytest.mark.parametrize("debug", [False, True])
def test_cli_starts_and_cleans_up_with_unavailable_log_directory(
    tmp_path, monkeypatch, capsys, debug
):
    import pult.app
    from pult.services.documents import material_rendering

    target = tmp_path / "blocked"
    target.write_text("keep")
    monkeypatch.setattr(diagnostics, "log_directory", lambda: target / "logs")
    monkeypatch.setattr(material_rendering, "initialize_graphics", lambda: None)
    closed = AsyncMock()

    async def run():
        assert capsys.readouterr() == ("", "")
        assert (
            asyncio.get_running_loop().get_exception_handler()
            is diagnostics.log_async_exception
        )

    app = SimpleNamespace(
        run_async=run, document_renderer=SimpleNamespace(close=closed)
    )

    def create_app(*, diagnostic_mode):
        assert diagnostic_mode is debug
        return app

    monkeypatch.setattr(pult.app, "PultApp", create_app)
    main(["--debug"] if debug else [])
    closed.assert_awaited_once()
    assert "Diagnoseprotokoll" in capsys.readouterr().err


def test_cli_records_startup_failure_and_closes_session(tmp_path, monkeypatch):
    from pult.services.documents import material_rendering

    monkeypatch.setattr(diagnostics, "log_directory", lambda: tmp_path)

    def broken_graphics():
        raise RuntimeError("PRIVATE_STARTUP_DETAIL")

    monkeypatch.setattr(material_rendering, "initialize_graphics", broken_graphics)
    with pytest.raises(RuntimeError):
        main([])
    text = (tmp_path / "pult.log").read_text()
    assert "application_failed" in text
    assert "session_stopped" in text
    assert "PRIVATE_" not in text


def test_keyboard_interrupt_still_propagates_and_closes_log(tmp_path, monkeypatch):
    from pult.services.documents import material_rendering

    monkeypatch.setattr(diagnostics, "log_directory", lambda: tmp_path)

    def interrupt():
        raise KeyboardInterrupt

    monkeypatch.setattr(material_rendering, "initialize_graphics", interrupt)
    with pytest.raises(KeyboardInterrupt):
        main([])
    text = (tmp_path / "pult.log").read_text()
    assert "session_interrupted" in text and "session_stopped" in text
    assert " ERROR " not in text


def test_readonly_exception_can_be_logged(logging_session):
    class ReadonlyError(Exception):
        def __setattr__(self, name, value):
            raise AttributeError(name)

    diagnostics.log_failure(
        logging.getLogger("pult.test"), "readonly_failure", ReadonlyError()
    )
    assert "readonly_failure" in logging_session.path.read_text()
