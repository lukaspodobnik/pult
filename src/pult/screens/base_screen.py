from typing import TYPE_CHECKING, TypeVar, cast

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
    @property
    def pult_app(self) -> "PultApp":
        return cast("PultApp", self.app)

    @property
    def app_config(self) -> AppConfig:
        return self.pult_app.require_config()

    @property
    def sequence_library(self) -> list[Sequence]:
        return self.pult_app.require_sequence_library().get_sequences()
