from pult.screens.confirmation_screen import ConfirmationScreen


class ConfirmUndoScreen(ConfirmationScreen):
    def __init__(self, school_class_id: str, subject_name: str | None = None) -> None:
        super().__init__(
            "Letzten Eintrag zurücknehmen",
            f"Klasse {school_class_id}"
            + (f" · {subject_name}" if subject_name else "")
            + "\n\nDie letzte Buchung wird aus dem Unterrichtsprotokoll entfernt. "
            "Ihre Auswirkungen auf den Fortschritt und die Terminplanung "
            "werden zurückgenommen.",
            confirm_id="confirm-undo",
            cancel_id="cancel-undo",
        )
