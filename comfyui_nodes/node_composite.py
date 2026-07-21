"""Node B — CompositeProductScene (post-generation, the heavy one).

Takes the generated (empty) background + the real product and produces the final
composite: tight-crop the product, fit it into the target box, land its base on
the surface line, and lay down a two-layer contact shadow — all in PIL. The
product's pixels are never regenerated (project rule #1-3).

Geometry math is reused verbatim from scripts/geometry.py. The compositing here
is a faithful PIL port of workflows/comfyui_api/composite_api.json (which the CLI
still drives over HTTP). Order: background -> soft spread shadow -> tight contact
core -> product. ComfyUI's ImageCompositeMasked == PIL paste(src,(x,y),mask).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageFilter

from . import tensor_io as TIO  # also puts ../scripts on sys.path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import geometry as G  # noqa: E402

# dark shadow colour, matching EmptyImage color=1710618 (0x1A1A1A) in the graph
_SHADOW_RGB = (26, 26, 26)


def _shadow_layer(alpha: Image.Image, w: int, h: int, blur: int,
                  opacity: float) -> tuple[Image.Image, Image.Image]:
    """Build one shadow layer from the product silhouette: squash-resize the
    alpha, blur it, scale by opacity -> (dark-gray patch, paste mask)."""
    w, h = max(1, w), max(1, h)
    shape = alpha.resize((w, h), Image.BILINEAR)
    if blur > 0:
        shape = shape.filter(ImageFilter.GaussianBlur(radius=blur))
    mask = shape.point(lambda p: int(p * opacity))          # silhouette * opacity
    patch = Image.new("RGB", (w, h), _SHADOW_RGB)
    return patch, mask


class CompositeProductScene:
    """background + product (IMAGE+MASK) + shadow_dir -> final composite IMAGE."""

    @classmethod
    def INPUT_TYPES(cls):
        f01 = {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}
        return {
            "required": {
                "background": ("IMAGE",),
                "product_image": ("IMAGE",),
                "product_mask": ("MASK",),
                # STRING (not a combo) so it can be wired from AnalyzeProductLighting's
                # shadow_dir output; also editable as a widget. Unknown values fall
                # back to "right" (geometry treats anything unknown as right).
                "shadow_dir": ("STRING", {"default": "right"}),
                "surface_line_frac": ("FLOAT", {"default": 0.78, "min": 0.0,
                                                "max": 1.0, "step": 0.01}),
                "target_width_frac": ("FLOAT", {"default": 0.6, "min": 0.05,
                                                "max": 1.0, "step": 0.01}),
                "target_height_frac": ("FLOAT", {"default": 0.42, "min": 0.05,
                                                 "max": 1.0, "step": 0.01}),
                "scale_mult": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 3.0,
                                         "step": 0.01}),
                "offset_x": ("INT", {"default": 0, "min": -2048, "max": 2048}),
                "offset_y": ("INT", {"default": 0, "min": -2048, "max": 2048}),
                "shadow_opacity": ("FLOAT", {"default": 0.30, "min": 0.0,
                                             "max": 1.0, "step": 0.01}),
                "shadow_blur": ("INT", {"default": 8, "min": 0, "max": 64}),
                "shadow_offset_y": ("INT", {"default": 0, "min": -512, "max": 512}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = "product-scene"

    def run(self, background, product_image, product_mask, shadow_dir,
            surface_line_frac, target_width_frac, target_height_frac, scale_mult,
            offset_x, offset_y, shadow_opacity, shadow_blur, shadow_offset_y):
        bg = TIO.image_to_pil(background).convert("RGB")
        frame_w, frame_h = bg.size

        shadow_dir = (shadow_dir or "right").strip().lower()
        if shadow_dir not in ("left", "right", "none"):
            shadow_dir = "right"

        # rebuild + tight-crop the product (raises NoAlphaError on a non-cut-out)
        rgba = TIO.product_to_rgba(product_image, product_mask)
        crop = G.tight_crop(rgba)

        overrides = {
            "scale_mult": scale_mult, "offset_x": offset_x, "offset_y": offset_y,
            "shadow_opacity": shadow_opacity, "shadow_blur": shadow_blur,
            "shadow_offset_y": shadow_offset_y,
        }
        target_box = {"width_frac": target_width_frac,
                      "height_frac": target_height_frac}
        g = G.compute(crop.width, crop.height, frame_w, frame_h, target_box,
                      surface_line_frac, overrides, shadow_dir)

        product = crop.resize((g.product_w, g.product_h), Image.LANCZOS)
        alpha = crop.getchannel("A")

        # background -> soft spread shadow -> tight contact core -> product
        spread_patch, spread_mask = _shadow_layer(
            alpha, g.shadow_w, g.shadow_h, g.shadow_blur, g.shadow_opacity)
        bg.paste(spread_patch, (g.shadow_x, g.shadow_y), spread_mask)

        core_patch, core_mask = _shadow_layer(
            alpha, g.core_w, g.core_h, g.core_blur, g.core_opacity)
        bg.paste(core_patch, (g.core_x, g.core_y), core_mask)

        bg.paste(product, (g.product_x, g.product_y), product)  # RGBA -> uses alpha

        return (TIO.pil_to_image(bg),)


NODE_CLASS_MAPPINGS = {"CompositeProductScene": CompositeProductScene}
NODE_DISPLAY_NAME_MAPPINGS = {"CompositeProductScene": "Composite Product Scene"}
