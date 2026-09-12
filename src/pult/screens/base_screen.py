from typing import TYPE_CHECKING, ClassVar, TypeVar, cast

from textual.binding import Binding
from textual.screen import ModalScreen, Screen

from pult.config import AppConfig
from pult.curriculum.sequence import Sequence

if TYPE_CHECKING:
    from pult.app import PultApp


ScreenResult = TypeVar("ScreenResult")


class PultScreen(Screen[ScreenResult]):
    @property
    def pult_app(self) -> "PultApp":
        return cast("PultApp", self.app)

    @property
    def app_config(self) -> AppConfig:
        return self.pult_app.require_config()

    @property
    def sequence_library(self) -> list[Sequence]:
        return self.pult_app.require_sequence_library().get_sequences()


class PultModalScreen(ModalScreen[ScreenResult]):
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
