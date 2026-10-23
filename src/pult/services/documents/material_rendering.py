"""Terminal-Grafikprotokoll einmalig vor dem Start von Textual erkennen."""

import sys

GRAPHICS = None
CELL = (10, 20)


def initialize_graphics():
    global GRAPHICS, CELL
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return
    from textual_image._terminal import get_cell_size
    from textual_image.widget import Image, SixelImage

    CELL = get_cell_size()
    # Only real graphics protocols. Half-block fallbacks cannot display readable documents.
    if Image is SixelImage:
        from pult.widgets.sixel_image import StableSixelImage

        GRAPHICS = StableSixelImage
    elif Image._Renderable.__module__.endswith(".tgp"):
        GRAPHICS = Image


def image_widget():
    return GRAPHICS
