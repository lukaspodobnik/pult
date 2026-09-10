"""Isolated adapter for the pinned textual-image 0.12.0 Sixel implementation.

Preserve glyph proportions when fitting terminal cells and keep a fixed formula
palette across scrolling crops. Uses private extension points for this experiment.
"""

import re

from PIL import Image as PILImage
from PIL import ImageColor, ImageOps
from rendering import BACKGROUND, FOREGROUND
from textual_image._pixeldata import PixelData
from textual_image._sixel import image_to_sixels
from textual_image.widget import SixelImage, SixelOptions
from textual_image.widget.sixel import _ImageSixelImpl


def terminal_safe_sixel(encoded):
    """Declare colors before painting and preserve already painted pixels.

    The encoder uses multiple overlaid color passes. P2=1 explicitly requests
    that zero bits preserve previous passes. Predeclaring the entire palette
    also avoids redefining color registers while an image is being painted.
    Raster dimensions and all actual drawing masks remain unchanged.
    """
    header = re.match(r'\x1bP0;0;0q"1;1;\d+;\d+', encoded)
    if header is None:
        raise ValueError("Unexpected Sixel header; check the pinned image library")
    definitions = re.compile(r"#(\d+);2;\d+;\d+;\d+")
    body = encoded[header.end() :]
    palette = "".join(match[0] for match in definitions.finditer(body))
    drawing = definitions.sub(lambda match: "#" + match[1], body)
    return header[0].replace("\x1bP0;0;0q", "\x1bP0;1;0q") + palette + drawing


def fit_image(image, width, height):
    canvas = PILImage.new("RGB", (width, height), BACKGROUND)
    fitted = ImageOps.contain(
        image.convert("RGB"), (width, height), PILImage.Resampling.LANCZOS
    )
    canvas.paste(fitted, (0, (height - fitted.height) // 2))
    return canvas


def formula_palette(image):
    """Fixed background-to-ink ramp, without spatial dithering."""
    background = ImageColor.getrgb(BACKGROUND)
    foreground = ImageColor.getrgb(FOREGROUND)
    palette = PILImage.new("P", (1, 1))
    palette.putpalette(
        [
            round(start + (end - start) * step / 255)
            for step in range(256)
            for start, end in zip(background, foreground)
        ]
    )
    return image.convert("RGB").quantize(palette=palette, dither=PILImage.Dither.NONE)


class StableSixelData(_ImageSixelImpl):
    def _scale_image(self, image_data, terminal_sizes):
        scaled = super()._scale_image(image_data, terminal_sizes)
        return PixelData(fit_image(image_data.pil_image, scaled.width, scaled.height))

    def _image_to_sixels(self, image, sixel_options=None, background=None):
        if self.parent.has_class("formula"):
            image = formula_palette(image)
        return terminal_safe_sixel(image_to_sixels(image, sixel_options, background))


class StableSixelImage(SixelImage, Renderable=SixelImage._Renderable):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
            sixel_options=SixelOptions(colors=256, smooth=None, quantize="adaptive"),
        )

    def compose(self):
        yield StableSixelData(self.image, self._sixel_options)
