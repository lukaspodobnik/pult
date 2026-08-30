from typing import TYPE_CHECKING, cast

from textual.screen import Screen

from schooltools_tui.config import AppConfig

if TYPE_CHECKING:
    from schooltools_tui.app import SchooltoolsApp


class SchooltoolsScreen(Screen[None]):

    @property
    def schooltools_app(self) -> "SchooltoolsApp":
        return cast("SchooltoolsApp", self.app)

    @property
    def app_config(self) -> AppConfig:
        return self.schooltools_app.require_config()
