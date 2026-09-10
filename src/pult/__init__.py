# Copyright (C) 2026 Lukas Podobnik
# SPDX-License-Identifier: GPL-3.0-or-later
# See COPYRIGHT and SOURCES.md for scope and third-party notices.


def main() -> None:
    from .services.material_rendering import initialize_graphics

    initialize_graphics()
    from .app import PultApp

    PultApp().run()
