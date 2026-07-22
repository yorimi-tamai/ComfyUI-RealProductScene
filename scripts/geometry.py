"""Product geometry auto-fit for the V2 composite pipeline.

Given a transparent product PNG and the frame/config, compute:
  - a tight-cropped product image (alpha bbox)  -> so bottom == contact line
  - scaled product size that fits the target box (proportional)
  - product placement (x, y) so its base sits on the surface line
  - a contact-shadow spec derived from the product's real base

Pure PIL math, no ComfyUI, no external models. Fully offline-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from PIL import Image, ImageFilter


class NoAlphaError(ValueError):
    """Raised when the input is not a transparent (de-backgrounded) PNG."""


@dataclass
class Geometry:
    # product (feeds composite node 65 ImageScale + node 69 ImageCompositeMasked)
    product_w: int
    product_h: int
    product_x: int
    product_y: int
    # contact-shadow sticker: an elliptical radial-gradient PNG (Phase 5) built
    # by shadow.py, scaled to shadow_w x shadow_h and placed at (shadow_x, shadow_y).
    # falloff / core_frac / feather are the sticker's own render params.
    shadow_w: int
    shadow_h: int
    shadow_x: int
    shadow_y: int
    shadow_opacity: float
    shadow_falloff: float
    shadow_core_frac: float
    shadow_feather: float
    # context
    surface_y: int

    def as_dict(self) -> dict:
        return asdict(self)


def load_transparent_png(path: str | Path) -> Image.Image:
    """Open an image and guarantee it has real transparency. Rejects JPG /
    fully-opaque PNG with a clear message (V1 excludes auto background removal)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"product image not found: {path}")
    img = Image.open(path)
    has_alpha = img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info)
    if not has_alpha:
        raise NoAlphaError(
            f"'{path.name}' has no alpha channel (mode={img.mode}). "
            f"V2 needs an already-background-removed PNG with transparency; "
            f"JPG or flat PNG is not supported (auto background removal is out of scope)."
        )
    img = img.convert("RGBA")
    lo, hi = img.getchannel("A").getextrema()
    if lo == 255:
        raise NoAlphaError(
            f"'{path.name}' is fully opaque (no transparent pixels) — it does "
            f"not look background-removed. Provide a cut-out product PNG."
        )
    return img


def tight_crop(img: Image.Image) -> Image.Image:
    """Crop to the alpha bounding box so the product touches all four edges."""
    bbox = img.getchannel("A").getbbox()
    if bbox is None:
        raise NoAlphaError("image is fully transparent — nothing to place.")
    return img.crop(bbox)


def defringe(img: Image.Image, erode_px: int = 2) -> Image.Image:
    """Shrink the alpha region by `erode_px` to kill the cut-out halo — the thin
    desaturated fringe a background-removal tool leaves on the product edge, which
    shows against any composite. A MinFilter of size (2*erode_px+1) erodes the
    alpha; RGB is untouched (Phase 7: product interior stays byte-for-byte).
    erode_px <= 0 is a no-op."""
    if erode_px <= 0:
        return img
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    a = a.filter(ImageFilter.MinFilter(2 * erode_px + 1))
    return Image.merge("RGBA", (r, g, b, a))


def compute(crop_w: int, crop_h: int, frame_w: int, frame_h: int,
            target_box: dict, surface_line_frac: float, overrides: dict,
            shadow_dir: str = "right") -> Geometry:
    """All placement math. Product base lands exactly on the surface line.
    `shadow_dir` (left|right|none) sets which way the cast shadow falls."""
    ov = {
        "scale_mult": 1.0, "offset_x": 0, "offset_y": 0,
        # Phase 5 shadow defaults, calibrated on the live basket render (task 8):
        # dense-ish, flat, a touch wider than the base -> hugs the product,
        # fades forward quickly (no long elliptical smudge).
        "shadow_opacity": 0.58, "shadow_offset_y": 0,
        "shadow_width_mult": 1.35, "shadow_flatten": 0.24,
        "shadow_falloff": 1.4, "shadow_core_frac": 0.28, "shadow_feather": 0.0,
        **(overrides or {}),
    }

    # 1. fit tight product into the target box, proportionally
    box_w = frame_w * float(target_box["width_frac"])
    box_h = frame_h * float(target_box["height_frac"])
    scale = min(box_w / crop_w, box_h / crop_h) * float(ov["scale_mult"])
    product_w = max(1, round(crop_w * scale))
    product_h = max(1, round(crop_h * scale))

    # 2. surface (contact) line + product placement (top-left of the source)
    surface_y = round(frame_h * float(surface_line_frac))
    product_x = round(frame_w / 2 - product_w / 2 + float(ov["offset_x"]))
    product_y = round(surface_y - product_h + float(ov["offset_y"]))

    # 3. contact shadow: a flattened ellipse centred on the contact point, a bit
    #    wider than the product base, nudged slightly toward the light-opposite
    #    side (light from left -> shadow falls right). The radial gradient (dense
    #    core -> soft tail) is baked by shadow.py; here we only size and place it.
    sign = {"left": -1, "right": 1, "none": 0}.get(shadow_dir, 1)
    off_y = float(ov["shadow_offset_y"])

    shadow_w = max(1, round(product_w * float(ov["shadow_width_mult"])))
    shadow_h = max(1, round(shadow_w * float(ov["shadow_flatten"])))
    shadow_cx = product_x + product_w / 2.0 + product_w * 0.06 * sign
    shadow_x = round(shadow_cx - shadow_w / 2.0)
    shadow_y = round(surface_y - shadow_h / 2.0 + off_y)

    return Geometry(
        product_w=product_w, product_h=product_h,
        product_x=product_x, product_y=product_y,
        shadow_w=shadow_w, shadow_h=shadow_h,
        shadow_x=shadow_x, shadow_y=shadow_y,
        shadow_opacity=float(ov["shadow_opacity"]),
        shadow_falloff=float(ov["shadow_falloff"]),
        shadow_core_frac=float(ov["shadow_core_frac"]),
        shadow_feather=float(ov["shadow_feather"]),
        surface_y=surface_y,
    )


def prepare_product(product_path: str | Path, cropped_out: str | Path,
                    frame_w: int, frame_h: int, target_box: dict,
                    surface_line_frac: float, overrides: dict,
                    shadow_dir: str = "right") -> Geometry:
    """End-to-end: validate + tight-crop + save cropped PNG + compute geometry.
    The cropped PNG at `cropped_out` is what gets uploaded to ComfyUI."""
    img = load_transparent_png(product_path)
    crop = tight_crop(img)
    Path(cropped_out).parent.mkdir(parents=True, exist_ok=True)
    crop.save(cropped_out)
    return compute(crop.width, crop.height, frame_w, frame_h,
                   target_box, surface_line_frac, overrides, shadow_dir)
