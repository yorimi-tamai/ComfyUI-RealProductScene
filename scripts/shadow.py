"""Phase 5 — procedural contact shadow (elliptical radial gradient).

Replaces the Phase 2.5 two-layer ComfyUI shadow (EmptyImage + uniform SolidMask
+ ImageBlur, done twice) which reads as a rounded *rectangle* with a flat centre
— square-ish edges, no falloff. Here we bake a single RGBA sticker whose alpha:

  - is an ELLIPSE (not a rectangle): zero outside the ellipse, so no square edge
  - falls off RADIALLY from the contact point outward: darkest under the product
    base, fading smoothly to nothing — this doubles as ambient-occlusion contact
    darkening (Phase 5 decision #1: AO folded into the shadow)
  - keeps a denser CORE near the centre (decision #3: one gradient subsumes the
    old core+spread pair — the core is the inner plateau, the spread is the tail)

Pure Pillow + numpy, no ComfyUI, fully offline-testable. geometry.py sizes and
places the sticker; generate.py uploads it; the composite graph just LoadImages
it and masks it onto the background under the product.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


def shadow_alpha(width: int, height: int, *, opacity: float = 0.55,
                 falloff: float = 1.8, core_frac: float = 0.18) -> np.ndarray:
    """Return an (H, W) float32 alpha map in [0, opacity].

    Elliptical radial gradient: alpha == opacity at the centre (and across the
    inner `core_frac` plateau), decreasing monotonically to 0 at the ellipse
    edge (normalised radius r == 1) and staying 0 outside it.

    - `falloff` shapes the tail: >1 concentrates darkness near the base (sharper
      contact), <1 spreads it wider and softer.
    - `core_frac` (0..1) is the inner radius kept fully opaque — the dense
      contact core. 0 disables the plateau (pure gradient from the centre).
    """
    width = max(1, int(width))
    height = max(1, int(height))
    opacity = float(np.clip(opacity, 0.0, 1.0))
    core_frac = float(np.clip(core_frac, 0.0, 0.95))

    # normalised coords centred at 0 with the OUTERMOST pixels landing exactly on
    # +/-1 (half-axis = (dim-1)/2), so the ellipse edge (radius 1) coincides with
    # the sticker border -> the outer ring is guaranteed to be fully transparent.
    ys = (np.arange(height, dtype=np.float32) - (height - 1) / 2.0)
    xs = (np.arange(width, dtype=np.float32) - (width - 1) / 2.0)
    ny = ys / max(1e-6, (height - 1) / 2.0)
    nx = xs / max(1e-6, (width - 1) / 2.0)
    r = np.sqrt(nx[None, :] ** 2 + ny[:, None] ** 2)  # (H, W) elliptical radius

    # inner plateau at full opacity, then a monotonic gradient to 0 at r == 1
    if core_frac >= 1.0 - 1e-6:
        t = (r <= 1.0).astype(np.float32)
    else:
        t = (1.0 - r) / (1.0 - core_frac)          # 1 at r=core_frac, 0 at r=1
        t = np.clip(t, 0.0, 1.0) ** float(falloff)
        t[r <= core_frac] = 1.0
    t[r >= 1.0] = 0.0
    return (t * opacity).astype(np.float32)


def radial_shadow(width: int, height: int, *, opacity: float = 0.55,
                  falloff: float = 1.8, core_frac: float = 0.18,
                  color: tuple[int, int, int] = (0, 0, 0),
                  feather: float = 0.0) -> Image.Image:
    """Build the RGBA contact-shadow sticker. `feather` (px) is an optional
    final Gaussian blur to soften the very edge; the gradient is already smooth,
    so it defaults off."""
    alpha = shadow_alpha(width, height, opacity=opacity, falloff=falloff,
                         core_frac=core_frac)
    h, w = alpha.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., 0] = int(color[0])
    rgba[..., 1] = int(color[1])
    rgba[..., 2] = int(color[2])
    rgba[..., 3] = np.round(alpha * 255.0).astype(np.uint8)
    img = Image.fromarray(rgba, mode="RGBA")
    if feather and feather > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=float(feather)))
    return img


# --- CLI: eyeball a sticker / dump its alpha profile ------------------------
def _main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="render a contact-shadow sticker")
    ap.add_argument("--width", type=int, default=400)
    ap.add_argument("--height", type=int, default=140)
    ap.add_argument("--opacity", type=float, default=0.55)
    ap.add_argument("--falloff", type=float, default=1.8)
    ap.add_argument("--core-frac", type=float, default=0.18)
    ap.add_argument("--feather", type=float, default=0.0)
    ap.add_argument("--out", default="outputs/composites/_shadow_preview.png")
    args = ap.parse_args(argv)

    img = radial_shadow(args.width, args.height, opacity=args.opacity,
                        falloff=args.falloff, core_frac=args.core_frac,
                        feather=args.feather)
    from pathlib import Path
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # flatten onto mid-grey so the shape is visible in a normal viewer
    bg = Image.new("RGBA", img.size, (128, 128, 128, 255))
    Image.alpha_composite(bg, img).save(out)
    a = shadow_alpha(args.width, args.height, opacity=args.opacity,
                     falloff=args.falloff, core_frac=args.core_frac)
    mid = a[a.shape[0] // 2]
    print(f"sticker {args.width}x{args.height} -> {out}")
    print(f"centre-row alpha: max={mid.max():.3f} edge={mid[0]:.3f} "
          f"monotonic={bool(np.all(np.diff(mid[:len(mid)//2]) >= -1e-6))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
