"""Lokale Diagnose, ohne Terminalausgabe oder Unterrichtsinhalte im Log."""

import asyncio
import hashlib
import logging
import os
import sys
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from importlib.metadata import PackageNotFoundError, version
from itertools import count
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import uuid4

MAX_LOG_BYTES = 5_000_000
LOG_BACKUPS = 3
_request: ContextVar[str] = ContextVar("pult_diagnostic_request", default="-")
_ids = count(1)
_session: "LoggingSession | None" = None


def log_directory() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "PULT"
    state = Path(os.environ.get("XDG_STATE_HOME", ""))
    if not state.is_absolute():
        state = Path.home() / ".local" / "state"
    return state / "pult" / "logs"


def package_version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "unknown"


def diagnostic_id(prefix: str) -> str:
    return f"{prefix}-{next(_ids)}"


def document_id(path: Path) -> str:
    """Dateien wiedererkennen, ohne Pfade oder Dateiinhalte zu protokollieren."""
    return hashlib.sha256(str(path).encode()).hexdigest()[:12]


@contextmanager
def operation(kind: str) -> Iterator[str]:
    request = diagnostic_id(kind)
    token = _request.set(request)
    try:
        yield request
    finally:
        _request.reset(token)


class DiagnosticFormatter(logging.Formatter):
    def formatException(self, ei) -> str:
        # Ausnahmetexte (auch von Browsern/Parsern) können ganze Dokumente oder
        # Eingaben enthalten. Nur Typen, Verkettung und Codestellen speichern.
        if ei[1] is None:
            return ""
        error = traceback.TracebackException.from_exception(ei[1], capture_locals=False)

        def frames(item: traceback.TracebackException) -> list[str]:
            result: list[str] = []
            if item.__cause__ is not None:
                result.extend(frames(item.__cause__))
                result.append("Caused by:")
            elif item.__context__ is not None and not item.__suppress_context__:
                result.extend(frames(item.__context__))
                result.append("During handling:")
            result.append("Traceback (exception text and locals omitted):")
            for frame in item.stack:
                result.append(f"  {frame.filename}:{frame.lineno} in {frame.name}")
            if item.exc_type is not None:
                result.append(
                    f"{item.exc_type.__module__}.{item.exc_type.__qualname__}"
                )
            for child in item.exceptions or ():
                result.extend(frames(child))
            return result

        return "\n".join(frames(error))


class SessionFilter(logging.Filter):
    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.session = self.session_id
        record.request = _request.get()
        return True


class QuietRotatingFileHandler(RotatingFileHandler):
    failed = False

    def handleError(self, record: logging.LogRecord) -> None:
        # logging's default handler prints to stderr, corrupting the TUI.
        self.failed = True

    def emit(self, record: logging.LogRecord) -> None:
        if not self.failed:
            super().emit(record)


class LoggingSession:
    def __init__(self, *, debug: bool, directory: Path):
        self.path = directory / "pult.log"
        self.logger = logging.getLogger("pult")
        self.previous_level = self.logger.level
        self.previous_propagate = self.logger.propagate
        self.closed = False
        self.unavailable = False
        self.handler: logging.Handler
        try:
            directory.mkdir(parents=True, exist_ok=True)
            handler = QuietRotatingFileHandler(
                self.path,
                maxBytes=MAX_LOG_BYTES,
                backupCount=LOG_BACKUPS,
                encoding="utf-8",
            )
            handler.addFilter(SessionFilter(uuid4().hex[:12]))
            handler.setFormatter(
                DiagnosticFormatter(
                    "%(asctime)s.%(msecs)03d %(levelname)s %(name)s "
                    "session=%(session)s request=%(request)s %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            self.handler = handler
        except OSError:
            self.unavailable = True
            self.handler = logging.NullHandler()
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.logger.propagate = False
        self.logger.addHandler(self.handler)
        self.logger.info(
            "session_started version=%s python=%s textual=%s platform=%s debug=%s",
            package_version("pult"),
            sys.version.split()[0],
            package_version("textual"),
            sys.platform,
            debug,
        )

    @property
    def failed(self) -> bool:
        return self.unavailable or (
            isinstance(self.handler, QuietRotatingFileHandler) and self.handler.failed
        )

    def close(self) -> None:
        if self.closed:
            return
        self.logger.info("session_stopped")
        self.logger.removeHandler(self.handler)
        try:
            self.handler.close()
        except OSError:
            self.unavailable = True
        self.logger.setLevel(self.previous_level)
        self.logger.propagate = self.previous_propagate
        self.closed = True


def configure_logging(
    *, debug: bool = False, directory: Path | None = None
) -> LoggingSession:
    global _session
    if _session is not None:
        _session.close()
    _session = LoggingSession(debug=debug, directory=directory or log_directory())
    return _session


def log_failure(
    logger: logging.Logger, event: str, error: BaseException, *args: object
) -> None:
    """Eine unerwartete Ausnahme auch beim Weiterreichen nur einmal erfassen."""
    if getattr(error, "_pult_logged", False):
        return
    logger.error(event, *args, exc_info=(type(error), error, error.__traceback__))
    try:
        setattr(error, "_pult_logged", True)
    except (AttributeError, TypeError):
        # Some exception classes disallow additional attributes. Logging must
        # never replace the original failure with a marking failure.
        pass


def log_async_exception(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    error = context.get("exception")
    logger = logging.getLogger("pult.asyncio")
    if isinstance(error, asyncio.CancelledError):
        logger.debug("async_task_cancelled")
    elif isinstance(error, BaseException):
        log_failure(logger, "async_task_failed", error)
    else:
        # Do not dump context: task/callback reprs can contain user input.
        logger.error("async_callback_failed exception_available=False")
