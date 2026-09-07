from schooltools_tui.screens.confirmation_screen import ConfirmationScreen
from schooltools_tui.services.closures import ScopedClosure


class ConfirmClosureDeletionScreen(ConfirmationScreen):
    def __init__(self, entry: ScopedClosure) -> None:
        scope = entry.school_class_id or "gesamte Schule"
        super().__init__(
            "Ausfall löschen",
            f"{entry.closure.name}\nGültig für: {scope}\n\n"
            "Dieser geplante Ausfall wird gelöscht und bei der Terminplanung "
            "nicht mehr berücksichtigt. Andere Ausfälle bleiben unverändert.",
            confirm_id="confirm-closure-deletion",
            cancel_id="cancel-closure-deletion",
        )
