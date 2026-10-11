import asyncio
import os
import shlex
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from pult.services.document_rendering import DocumentRenderer
from pult.services.renderer_setup import RendererSetup, dependency_help, setup_failure

REAL_CHECK = DocumentRenderer.check_available


@pytest.mark.parametrize("distro, release", [("ubuntu", "24.04"), ("debian", "13")])
def test_supported_linux_uses_pults_interpreter(monkeypatch, distro, release):
    monkeypatch.setattr(
        "pult.services.renderer_setup.linux_release",
        lambda: {"ID": distro, "VERSION_ID": release},
    )
    monkeypatch.setattr(sys, "executable", "/home/test user/pult/bin/python")
    help_text, command = dependency_help("Missing libraries: libnss3.so")
    assert shlex.split(command) == [
        sys.executable,
        "-m",
        "playwright",
        "install-deps",
        "chromium",
    ]
    assert "Administratorrechte" in help_text


@pytest.mark.parametrize(
    "release", [{"ID": "arch"}, {"ID": "omarchy", "ID_LIKE": "arch"}]
)
def test_arch_offers_library_lookup_not_debian_installer(monkeypatch, release):
    monkeypatch.setattr("pult.services.renderer_setup.linux_release", lambda: release)
    help_text, command = dependency_help(
        "Missing libraries: libnss3.so\nlibnspr4.so\nlibnss3.so"
    )
    assert shlex.split(command) == ["pacman", "-F", "libnspr4.so", "libnss3.so"]
    assert "nicht offiziell" in help_text
    assert "install-deps" not in command + help_text


@pytest.mark.parametrize(
    "release", [{}, {"ID": "fedora"}, {"ID": "ubuntu", "VERSION_ID": "20.04"}]
)
def test_unknown_or_unsupported_linux_never_guesses_package_commands(
    monkeypatch, release
):
    monkeypatch.setattr("pult.services.renderer_setup.linux_release", lambda: release)
    assert dependency_help("Missing libraries: example.so")[1] == ""


def test_error_classification_keeps_diagnostics():
    for details, state in [
        ("BrowserType.launch: Executable doesn't exist at /cache/chrome", "missing"),
        ("Host system is missing dependencies to run browsers.", "dependencies"),
        ("error while loading shared libraries: libnss3.so", "dependencies"),
        ("Permission denied: /cache/chrome", "failed"),
    ]:
        result = setup_failure(RuntimeError(details))
        assert result.state == state
        assert result.details == details


def test_later_is_remembered_only_for_current_playwright_version(tmp_path):
    setup = RendererSetup(DocumentRenderer(tmp_path / "new/cache/documents"))
    assert setup.should_offer()
    setup.defer()
    assert not setup.should_offer()
    setup.revision += "-updated"
    assert setup.should_offer()


def test_probe_reports_real_failure_and_timeout(tmp_path):
    async def run():
        renderer = DocumentRenderer(tmp_path)
        setup = RendererSetup(renderer)
        renderer.check_available = AsyncMock(
            side_effect=RuntimeError("Executable doesn't exist")
        )
        assert (await setup.check()).state == "missing"
        renderer.check_available = AsyncMock(side_effect=TimeoutError())
        assert "zu lange" in (await setup.check()).message

    asyncio.run(run())


def test_check_can_restart_a_disconnected_browser(tmp_path):
    async def run():
        renderer = DocumentRenderer(tmp_path)
        renderer.browser = SimpleNamespace(is_connected=lambda: False)
        replacement = SimpleNamespace(is_connected=lambda: True)
        launch = AsyncMock(return_value=replacement)
        renderer.driver = SimpleNamespace(chromium=SimpleNamespace(launch=launch))
        await renderer.ensure_browser()
        assert renderer.browser is replacement
        await renderer.ensure_browser()
        launch.assert_awaited_once()

    asyncio.run(run())


@pytest.mark.parametrize(
    "returncode, details, expected",
    [
        (0, "Downloaded", "ready"),
        (1, "Network unavailable", "missing"),
        (1, "Host system is missing dependencies", "dependencies"),
    ],
)
def test_download_uses_own_environment_and_checks_result(
    tmp_path, monkeypatch, returncode, details, expected
):
    async def run():
        stream = asyncio.StreamReader()
        stream.feed_data(details.encode())
        stream.feed_eof()
        process = SimpleNamespace(
            stdout=stream, wait=AsyncMock(return_value=returncode)
        )
        spawn = AsyncMock(return_value=process)
        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        renderer = DocumentRenderer(tmp_path)
        renderer.reset = AsyncMock()
        renderer.check_available = AsyncMock()
        output = []
        result = await RendererSetup(renderer).install(output.append)
        assert result.state == expected
        assert spawn.call_args.args == (
            sys.executable,
            "-m",
            "playwright",
            "install",
            "chromium",
            "--only-shell",
        )
        assert "shell" not in spawn.call_args.kwargs
        assert output == [details]
        assert renderer.reset.await_count == (1 if returncode == 0 else 0)
        assert renderer.check_available.await_count == (1 if returncode == 0 else 0)

    asyncio.run(run())


@pytest.mark.skipif(os.name != "posix", reason="Prozessgruppen unter macOS/Linux")
@pytest.mark.parametrize("cancel_during_spawn", [False, True])
def test_cancel_stops_installer_and_child_even_during_spawn(
    tmp_path, monkeypatch, cancel_during_spawn
):
    async def run():
        spawn = asyncio.create_subprocess_exec
        started = asyncio.Event()
        output_seen = asyncio.Event()
        processes = []
        marker = tmp_path / "orphan.txt"
        child_code = (
            "import time,pathlib; time.sleep(.6); "
            f"pathlib.Path({str(marker)!r}).write_text('orphan')"
        )
        parent_code = (
            "import subprocess,sys,time; "
            f"subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
            "print('started',flush=True); time.sleep(30)"
        )

        async def start(*args, **kwargs):
            started.set()
            if cancel_during_spawn:
                await asyncio.sleep(0.05)
            process = await spawn(sys.executable, "-c", parent_code, **kwargs)
            processes.append(process)
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", start)
        setup = RendererSetup(DocumentRenderer(tmp_path / "cache"))
        task = asyncio.create_task(setup.install(lambda _: output_seen.set()))
        await asyncio.wait_for(
            started.wait() if cancel_during_spawn else output_seen.wait(), 3
        )
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 5)
        assert processes[0].returncode is not None
        await asyncio.sleep(0.7)
        assert not marker.exists()
        assert not setup.lock.locked()

    asyncio.run(run())


@pytest.mark.skipif(
    not os.environ.get("PULT_TEST_BROWSER"), reason="Expliziter lokaler Browser-Test"
)
def test_browser_probe_and_reset_refresh_fonts_and_existing_documents(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(DocumentRenderer, "check_available", REAL_CHECK)

    async def run():
        renderer = DocumentRenderer(tmp_path)
        renderer._avenir_available = False
        try:
            assert (await RendererSetup(renderer).check()).state == "ready"
            assert renderer._avenir_available is None
            assert renderer.generation == 1
            await renderer.reset()
            assert renderer.browser is None and renderer.driver is None
            assert renderer.generation == 2
        finally:
            await renderer.close()

    asyncio.run(run())


def test_arch_handles_playwright_reporting_only_debian_packages(monkeypatch):
    monkeypatch.setattr(
        "pult.services.renderer_setup.linux_release", lambda: {"ID": "arch"}
    )
    help_text, command = dependency_help(
        "Host system is missing dependencies. sudo apt-get install libnss3 libnspr4"
    )
    assert command == ""
    assert "Debian-Pakete" in help_text
    assert "Dateisuche unten" not in help_text
