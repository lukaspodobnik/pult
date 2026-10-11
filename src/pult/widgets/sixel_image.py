"""Isolated adapter for the pinned textual-image 0.12.0 Sixel implementation.

Preserve image proportions when fitting terminal cells and declare the palette
before drawing scrolling crops. Uses private extension points for textual-image 0.12.0.
"""

import re

from PIL import Image as PILImage
from PIL import ImageOps
from textual_image._pixeldata import PixelData
from textual_image._sixel import image_to_sixels
from textual_image.widget import SixelImage, SixelOptions
from textual_image.widget.sixel import _ImageSixelImpl

BACKGROUND = "#18252b"


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


def fit_image(image, width, height, background):
    canvas = PILImage.new("RGB", (width, height), background)
    fitted = ImageOps.contain(
        image.convert("RGB"), (width, height), PILImage.Resampling.LANCZOS
    )
    canvas.paste(fitted, (0, (height - fitted.height) // 2))
    return canvas


class StableSixelData(_ImageSixelImpl):
    def _scale_image(self, image_data, terminal_sizes):
        assert isinstance(self.parent, StableSixelImage)
        scaled = super()._scale_image(image_data, terminal_sizes)
        return PixelData(
            fit_image(
                image_data.pil_image,
                scaled.width,
                scaled.height,
                self.parent.paper_color,
            )
        )

    def _image_to_sixels(self, image, sixel_options=None, background=None):
        assert isinstance(self.parent, StableSixelImage)
        return terminal_safe_sixel(image_to_sixels(image, sixel_options, background))


class StableSixelImage(SixelImage, Renderable=SixelImage._Renderable):
    def __init__(self, *args, paper_color=BACKGROUND, **kwargs):
        self.paper_color = paper_color
        super().__init__(
            *args,
            **kwargs,
            sixel_options=SixelOptions(colors=256, smooth=None, quantize="adaptive"),
        )

    def compose(self):
        yield StableSixelData(self.image, self._sixel_options)
