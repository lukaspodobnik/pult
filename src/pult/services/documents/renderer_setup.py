"""Chromium im PULT-Interpreter einrichten; Systempakete bleiben beim Nutzer."""

import asyncio
import os
import platform
import re
import shlex
import signal
import sys
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import version
from typing import Literal

from pult.services.documents.document_rendering import DocumentRenderer
from pult.storage import save_text

SetupState = Literal["ready", "missing", "dependencies", "failed"]


@dataclass(frozen=True)
class SetupResult:
    state: SetupState
    message: str
    details: str = ""
    help: str = ""
    command: str = ""


def linux_release() -> dict[str, str]:
    if sys.platform != "linux":
        return {}
    try:
        return platform.freedesktop_os_release()
    except OSError:
        return {}


def dependency_help(details: str) -> tuple[str, str]:
    release = linux_release()
    distro, release_version = release.get("ID"), release.get("VERSION_ID")
    if (distro == "debian" and release_version in {"12", "13"}) or (
        distro == "ubuntu" and release_version in {"22.04", "24.04", "26.04"}
    ):
        return (
            "Fehlende Systembibliotheken im Terminal installieren (benötigt "
            "Administratorrechte). Danach hier erneut prüfen.",
            shlex.join(
                [sys.executable, "-m", "playwright", "install-deps", "chromium"]
            ),
        )
    if distro == "arch" or "arch" in release.get("ID_LIKE", "").split():
        libraries = sorted(set(re.findall(r"\blib[\w+-]+\.so(?:\.\d+)*", details)))
        if not libraries:
            return (
                "Arch/Omarchy: Systembibliotheken über pacman ergänzen. "
                "Playwright nennt in den Details möglicherweise Debian-Pakete; "
                "deren Namen müssen für Arch übersetzt werden. Danach erneut prüfen. "
                "Playwright unterstützt Arch nicht offiziell.",
                "",
            )
        return (
            "Arch/Omarchy: Fehlende Bibliotheken über pacman ergänzen. "
            "Die Dateisuche unten zeigt die zugehörigen Pakete; bei fehlender "
            "Dateidatenbank zuerst sudo pacman -Fy ausführen. "
            "Danach die gefundenen Pakete mit sudo pacman -S --needed installieren "
            "und hier erneut prüfen. Playwright unterstützt Arch nicht offiziell.",
            shlex.join(["pacman", "-F", *libraries]),
        )
    return (
        "Die in den Details genannten Systembibliotheken über den Paketmanager "
        "deiner Distribution installieren, danach hier erneut prüfen. "
        "Für dieses System gibt es in PULT keinen geprüften Installationsbefehl.",
        "",
    )


def setup_failure(error: Exception) -> SetupResult:
    details = str(error)
    if "Executable doesn't exist" in details:
        return SetupResult(
            "missing",
            "Für Dokumentgrafik und PDF-Export fehlt die passende Chromium-Version. "
            "PULT kann sie herunterladen. Die Textansicht funktioniert auch ohne sie.",
            details,
        )
    if any(
        marker in details
        for marker in (
            "Host system is missing dependencies",
            "Missing libraries:",
            "error while loading shared libraries",
        )
    ):
        help_text, command = dependency_help(details)
        return SetupResult(
            "dependencies",
            "Chromium benötigt zusätzliche Systembibliotheken.",
            details,
            help_text,
            command,
        )
    return SetupResult(
        "failed",
        "Die Dokumentdarstellung konnte nicht geprüft werden. "
        "Die Details helfen bei der Fehlersuche; die Textansicht bleibt nutzbar.",
        details or type(error).__name__,
    )


async def stop_installer(process: asyncio.subprocess.Process) -> None:
    """Auch die vom Python-Einstiegspunkt gestarteten Downloadprozesse beenden."""

    def send(sig: signal.Signals) -> None:
        try:
            if os.name == "posix":
                os.killpg(process.pid, sig)
            elif process.returncode is None:
                process.terminate() if sig == signal.SIGTERM else process.kill()
        except ProcessLookupError:
            pass

    send(signal.SIGTERM)
    try:
        await asyncio.wait_for(process.communicate(), timeout=3)
    except TimeoutError:
        send(signal.SIGKILL)
        await process.communicate()


class RendererSetup:
    def __init__(self, renderer: DocumentRenderer):
        self.renderer = renderer
        self.state_path = renderer.cache.parent / "renderer-setup.txt"
        # Nach einem Playwright-Update erneut anbieten: es braucht ggf. neue Browser.
        self.revision = f"{sys.platform}:{version('playwright')}"
        self.lock = asyncio.Lock()

    def should_offer(self) -> bool:
        try:
            return self.state_path.read_text(encoding="utf-8").strip() != self.revision
        except (OSError, UnicodeError):
            return True

    def defer(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        save_text(self.state_path, self.revision + "\n")

    async def check(self) -> SetupResult:
        async with self.lock:
            return await self._check()

    async def _check(self) -> SetupResult:
        try:
            async with asyncio.timeout(30):
                await self.renderer.check_available()
            return SetupResult(
                "ready", "Dokumentdarstellung und PDF-Export sind bereit."
            )
        except TimeoutError:
            return SetupResult(
                "failed", "Die Prüfung hat zu lange gedauert. Bitte erneut versuchen."
            )
        except Exception as error:
            return setup_failure(error)

    async def install(self, output: Callable[[str], None]) -> SetupResult:
        async with self.lock:
            # Derselbe Interpreter wie PULT, auch bei uv tool install --editable.
            command = [
                sys.executable,
                "-m",
                "playwright",
                "install",
                "chromium",
                "--only-shell",
            ]
            environment = {**os.environ, "CI": "1", "NO_COLOR": "1"}
            environment.pop("FORCE_COLOR", None)
            spawn = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    start_new_session=os.name == "posix",
                    env=environment,
                )
            )
            process = None
            log = ""
            try:
                # Ein Abbruch während des Starts darf keinen Prozess zurücklassen.
                process = await asyncio.shield(spawn)
                async with asyncio.timeout(600):
                    assert process.stdout is not None
                    while chunk := await process.stdout.read(2048):
                        log = (log + chunk.decode("utf-8", errors="replace"))[-12000:]
                        output(log)
                    returncode = await process.wait()
                if returncode:
                    failure = setup_failure(RuntimeError(log))
                    if failure.state == "dependencies":
                        return failure
                    return SetupResult(
                        "missing",
                        "Die Einrichtung ist fehlgeschlagen. Bitte die Details prüfen "
                        "und erneut versuchen.",
                        log,
                    )
                await self.renderer.reset()
                return await self._check()
            except asyncio.CancelledError:
                if process is None:
                    try:
                        process = await spawn
                    except OSError:
                        pass
                if process is not None:
                    await stop_installer(process)
                raise
            except (OSError, TimeoutError) as error:
                if process is not None:
                    await stop_installer(process)
                return SetupResult(
                    "missing",
                    "Die Einrichtung konnte nicht abgeschlossen werden. "
                    "Bitte erneut versuchen.",
                    log + "\n" + (str(error) or "Zeitlimit für den Download erreicht."),
                )
