"""Tensor <-> PIL conversion at the ComfyUI node boundary.

ComfyUI passes images as torch tensors (IMAGE = [B,H,W,C] float 0-1, RGB) and
transparency as a separate MASK ([B,H,W] float 0-1). The V2 "brain" works in
PIL RGBA, so every node converts on the way in and out; the internal logic is
never rewritten (Phase 4 decision #3).

Key convention: ComfyUI's LoadImage emits MASK = 1 - alpha (0 where fully
opaque). We invert it back to an alpha channel to rebuild the cut-out product.
A missing / size-mismatched / fully-opaque mask means the input is not a
background-removed PNG -> we raise NoAlphaError (same guard the CLI uses).

`torch` is imported lazily (only pil_to_image needs it) so this module — and the
alpha guard in particular — is unit-testable in a numpy+Pillow environment
without a full torch install. The live path in ComfyUI always has torch.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

# reuse the canonical guard error from the shared brain
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from geometry import NoAlphaError  # noqa: E402


def _to_numpy(x):
    """torch tensor (CPU/GPU) or numpy array -> numpy array, no hard torch dep."""
    if hasattr(x, "detach"):        # torch tensor
        x = x.detach().cpu()
    return np.asarray(x)


def image_to_pil(image) -> Image.Image:
    """ComfyUI IMAGE [B,H,W,C] float 0-1 -> PIL RGB (first item of the batch)."""
    arr = _to_numpy(image)
    if arr.ndim == 4:
        arr = arr[0]
    arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def product_to_rgba(image, mask) -> Image.Image:
    """Rebuild an RGBA product PIL from a ComfyUI IMAGE + MASK pair.

    Raises NoAlphaError when the mask is absent, the wrong size (e.g. the 64x64
    placeholder LoadImage emits for a flat image), or fully opaque — all signs
    the input was not background-removed."""
    rgb = image_to_pil(image)
    w, h = rgb.size

    if mask is None:
        raise NoAlphaError(
            "no product MASK connected. Wire LoadImage's MASK output from a "
            "background-removed PNG (auto background removal is out of scope)."
        )
    m = _to_numpy(mask).astype(np.float32)
    if m.ndim == 3:
        m = m[0]
    if m.shape != (h, w):
        raise NoAlphaError(
            f"product MASK {m.shape} does not match the image {(h, w)} — this "
            f"usually means the product PNG has no alpha channel. Provide a "
            f"cut-out (background-removed) PNG with real transparency."
        )

    alpha = np.clip((1.0 - m) * 255.0, 0, 255).astype(np.uint8)
    if int(alpha.min()) >= 255:
        raise NoAlphaError(
            "product is fully opaque (no transparent pixels) — it does not look "
            "background-removed. Provide a cut-out product PNG."
        )

    rgba = rgb.convert("RGBA")
    rgba.putalpha(Image.fromarray(alpha, "L"))
    return rgba


def pil_to_image(pil: Image.Image):
    """PIL image -> ComfyUI IMAGE tensor [1,H,W,3] float 0-1 (RGB)."""
    import torch  # lazy: only the output path needs torch
    arr = np.asarray(pil.convert("RGB")).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]
