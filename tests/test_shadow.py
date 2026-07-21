"""Unit tests for the Phase 5 contact-shadow sticker (scripts/shadow.py):
elliptical radial gradient — monotonic falloff, zero at/outside the ellipse edge,
dense core plateau, falloff shaping. Offline, no ComfyUI.
Run with the ComfyUI .venv python:  python tests/test_shadow.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import shadow as SH


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    return bool(cond)


def main() -> int:
    ok = True
    W, H, OP = 400, 160, 0.6
    a = SH.shadow_alpha(W, H, opacity=OP, falloff=1.8, core_frac=0.18)

    # shape + range
    ok &= check("shape is (H, W)", a.shape == (H, W))
    ok &= check("alpha within [0, opacity]", a.min() >= 0.0 and a.max() <= OP + 1e-6)
    ok &= check("centre reaches opacity", abs(a[H // 2, W // 2] - OP) < 1e-6)

    # centre-row: monotonic non-increasing from centre outward to the edge
    row = a[H // 2]
    right = row[W // 2:]
    ok &= check("centre->right edge monotonic non-increasing",
                bool(np.all(np.diff(right) <= 1e-6)))
    ok &= check("right edge alpha == 0", right[-1] == 0.0)
    col = a[:, W // 2]
    down = col[H // 2:]
    ok &= check("centre->bottom edge monotonic non-increasing",
                bool(np.all(np.diff(down) <= 1e-6)))
    ok &= check("bottom edge alpha == 0", down[-1] == 0.0)

    # ellipse, not rectangle: the four corners are OUTSIDE the ellipse -> 0,
    # while a rectangle-blur shadow would still carry weight there.
    corners = [a[0, 0], a[0, -1], a[-1, 0], a[-1, -1]]
    ok &= check("all four corners are 0 (elliptical, not square)",
                all(c == 0.0 for c in corners))
    # a point just inside the rectangle corner region but outside the ellipse
    ok &= check("near-corner (rect-inside, ellipse-outside) is 0",
                a[int(H * 0.08), int(W * 0.08)] == 0.0)

    # dense core plateau: inside core_frac radius alpha stays at opacity
    core = SH.shadow_alpha(W, H, opacity=OP, falloff=1.8, core_frac=0.30)
    # a point well inside the core radius on the centre row
    x_in = W // 2 + int((0.30 * 0.5) * (W / 2) * 0.5)  # clearly inside plateau
    ok &= check("core plateau at full opacity", abs(core[H // 2, x_in] - OP) < 1e-6)

    # falloff shaping: a sharper falloff makes a mid-radius sample darker-drop
    soft = SH.shadow_alpha(W, H, opacity=OP, falloff=0.8, core_frac=0.0)
    hard = SH.shadow_alpha(W, H, opacity=OP, falloff=3.0, core_frac=0.0)
    xm = W // 2 + (W // 2) // 2  # ~half-way to the right edge
    ok &= check("higher falloff -> less alpha at mid radius",
                hard[H // 2, xm] < soft[H // 2, xm])

    # core_frac=1 -> solid ellipse (all inside == opacity, outside == 0)
    solid = SH.shadow_alpha(60, 60, opacity=OP, falloff=1.8, core_frac=1.0)
    ok &= check("core_frac=1 is a solid ellipse (centre==opacity, corner==0)",
                abs(solid[30, 30] - OP) < 1e-6 and solid[0, 0] == 0.0)

    # RGBA sticker sanity
    img = SH.radial_shadow(W, H, opacity=OP)
    ok &= check("radial_shadow returns RGBA of right size",
                img.mode == "RGBA" and img.size == (W, H))

    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
