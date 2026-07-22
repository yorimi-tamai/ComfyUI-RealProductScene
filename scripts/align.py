"""Phase 7 swap-backend alignment.

The swap backend feeds a GPT-generated FULL scene (the product is already drawn
into it by GPT) as a template. We locate WHERE GPT drew that product, then place
the user's REAL product PNG over the same spot so it inherits the scene's baked
shadow/light while keeping the real product's pixels.

Locating is a multi-scale masked template match (opencv): the real product's
tight crop is the template, the scene is the image. Because the user feeds the
real product to GPT as a reference, GPT's rendered look-alike is nearly identical
in shape/pose, so normalized cross-correlation locks on tightly.

Output is a `geometry.Geometry` (the same struct the composite consumes), with
the shadow fields zeroed — swap never bakes a shadow (it comes from the scene).

Pure numpy/opencv/PIL, offline-testable. opencv is only imported here, so the
comfyui/manual backends stay dependency-clean.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

import geometry as G


@dataclass
class AlignResult:
    """Where GPT's product sits in the scene (pixels), plus match diagnostics."""
    x: int
    y: int
    w: int
    h: int
    score: float      # best TM_CCORR_NORMED correlation (0..1)
    scale: float      # template scale that won

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)


def _template_gray(crop_rgba: Image.Image) -> np.ndarray:
    """Grayscale of the product crop with transparent pixels filled with the
    opaque-region mean. TM_CCOEFF_NORMED subtracts the local mean, so a flat
    mean-fill in the see-through areas (bow gaps, corners) contributes ~nothing
    instead of injecting fake edges — this is why we fill rather than mask
    (CCOEFF has no mask support, and CCORR's masked form is scale-biased)."""
    import cv2
    arr = np.asarray(crop_rgba.convert("RGBA"))
    gray = cv2.cvtColor(arr[..., :3], cv2.COLOR_RGB2GRAY)
    alpha = arr[..., 3]
    opaque = alpha > 8
    fill = int(gray[opaque].mean()) if opaque.any() else 0
    out = np.where(opaque, gray, fill).astype(np.uint8)
    return np.ascontiguousarray(out)


def _scene_gray(scene_path: str | Path) -> np.ndarray:
    """Load the scene as grayscale via PIL (robust to unicode/space paths, unlike
    cv2.imread) then to a numpy uint8 array."""
    import cv2
    with Image.open(scene_path) as im:
        arr = np.asarray(im.convert("RGB"))
    return np.ascontiguousarray(cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY))


def _match_at_scale(scene_g: np.ndarray, tmpl_g: np.ndarray, scale: float):
    """Resize template by `scale`, run one match (TM_CCOEFF_NORMED — mean-
    subtracted, robust to brightness and comparable across scales). Returns
    (score, x, y, w, h) or None if the scaled template does not fit the scene."""
    import cv2
    ch, cw = tmpl_g.shape[:2]
    w, h = max(1, round(cw * scale)), max(1, round(ch * scale))
    sh, sw = scene_g.shape[:2]
    if w >= sw or h >= sh:
        return None
    t = cv2.resize(tmpl_g, (w, h), interpolation=cv2.INTER_AREA)
    res = cv2.matchTemplate(scene_g, t, cv2.TM_CCOEFF_NORMED)
    res = np.nan_to_num(res, nan=-1.0, posinf=-1.0, neginf=-1.0)
    _minv, maxv, _minl, maxl = cv2.minMaxLoc(res)
    return float(maxv), int(maxl[0]), int(maxl[1]), w, h


def locate_product(scene_path: str | Path, crop_rgba: Image.Image,
                   scale_min: float = 0.3, scale_max: float = 2.5) -> AlignResult:
    """Two-pass multi-scale template match. Coarse sweep over
    [scale_min, scale_max], then a fine sweep around the best scale. The ceiling
    is generous (2.5) because the product crop can be much smaller than GPT's
    rendered version — too low a ceiling clamps the match to a wrong scale (the
    shoe example locked at 1.75, score .75, vs a false .51 when capped at 1.5).
    A best scale at the ceiling means the true match may be larger — see the
    warning in the caller."""
    scene_g = _scene_gray(scene_path)
    tmpl_g = _template_gray(crop_rgba)

    def sweep(lo: float, hi: float, step: float):
        best = None
        s = lo
        while s <= hi + 1e-9:
            r = _match_at_scale(scene_g, tmpl_g, s)
            if r is not None and (best is None or r[0] > best[0]):
                best = (r[0], r[1], r[2], r[3], r[4], s)
            s += step
        return best

    coarse = sweep(scale_min, scale_max, 0.05)
    if coarse is None:
        raise ValueError("template match failed: product does not fit the scene "
                         "at any tested scale")
    bs = coarse[5]
    fine = sweep(max(scale_min, bs - 0.06), min(scale_max, bs + 0.06), 0.01)
    best = fine if (fine is not None and fine[0] >= coarse[0]) else coarse
    score, x, y, w, h, scale = best
    if scale >= scale_max - 0.02:
        print(f"⚠️  align hit the scale ceiling ({scale_max}); the real match may be "
              f"larger — raise scale_max or nudge with --scale-mult")
    return AlignResult(x=x, y=y, w=w, h=h, score=score, scale=scale)


def build_swap_geometry(align: AlignResult, overrides: dict | None = None,
                        cover_margin: float = 0.03) -> G.Geometry:
    """Turn the located bbox into the Geometry the composite consumes. Manual
    knobs layer on top of the auto result: scale_mult resizes about the bbox
    centre, offset_x/y nudge it. `cover_margin` (force-cover) scales the product
    up a touch (default 3%) so it reliably blankets GPT's fake product — the
    residual fringe then falls on the real product's own edge, not GPT's leftover
    pixels. Shadow fields are zeroed (swap skips bake_shadow)."""
    ov = {"scale_mult": 1.0, "offset_x": 0, "offset_y": 0, **(overrides or {})}
    eff_scale = float(ov["scale_mult"]) * (1.0 + max(0.0, cover_margin))
    w = max(1, round(align.w * eff_scale))
    h = max(1, round(align.h * eff_scale))
    cx = align.x + align.w / 2.0 + float(ov["offset_x"])
    cy = align.y + align.h / 2.0 + float(ov["offset_y"])
    px = round(cx - w / 2.0)
    py = round(cy - h / 2.0)
    return G.Geometry(
        product_w=w, product_h=h, product_x=px, product_y=py,
        shadow_w=0, shadow_h=0, shadow_x=0, shadow_y=0,
        shadow_opacity=0.0, shadow_falloff=0.0, shadow_core_frac=0.0,
        shadow_feather=0.0,
        surface_y=py + h,
    )
