import logging
from typing import TYPE_CHECKING, ClassVar, TypeVar, cast

from textual.binding import Binding
from textual.screen import ModalScreen, Screen
from textual.worker import Worker, WorkerState

from pult.config import AppConfig
from pult.curriculum.sequence import Sequence
from pult.services.diagnostics import log_failure

if TYPE_CHECKING:
    from pult.app import PultApp


ScreenResult = TypeVar("ScreenResult")


class WorkerDiagnostics:
    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        worker = event.worker
        logger = logging.getLogger(__name__)
        if event.state is WorkerState.ERROR and not worker.exit_on_error:
            if worker.error is not None:
                log_failure(
                    logger,
                    "background_worker_failed screen=%s group=%s",
                    worker.error,
                    type(self).__name__,
                    worker.group,
                )
        elif event.state is WorkerState.CANCELLED:
            logger.debug(
                "worker_cancelled screen=%s group=%s", type(self).__name__, worker.group
            )


class PultScreen(WorkerDiagnostics, Screen[ScreenResult]):
    @property
    def pult_app(self) -> "PultApp":
        return cast("PultApp", self.app)

    @property
    def app_config(self) -> AppConfig:
        return self.pult_app.require_config()

    @property
    def sequence_library(self) -> list[Sequence]:
        return self.pult_app.require_sequence_library().get_sequences()


class PultModalScreen(WorkerDiagnostics, ModalScreen[ScreenResult]):
    BINDINGS: ClassVar = [Binding("f1", "show_binding_help", "Hilfe", priority=True)]

    def action_show_binding_help(self) -> None:
        self.pult_app.action_show_binding_help()

    @property
    def pult_app(self) -> "PultApp":
        return cast("PultApp", self.app)

    @property
    def app_config(self) -> AppConfig:
        return self.pult_app.require_config()

    @property
    def sequence_library(self) -> list[Sequence]:
        return self.pult_app.require_sequence_library().get_sequences()
