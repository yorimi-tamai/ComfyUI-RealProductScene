"""Offline unit tests for detect_surface — pure logic, no torch / no model.

Exercises the depth-analysis heuristics on synthetic depth maps and the
never-crash fallback path (missing model). Live end-to-end quality is validated
separately against tests/fixtures/phase3-surface/ (Task 4). Run with the
ComfyUI .venv python (has numpy):
    python tests/test_detect_surface.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import detect_surface as DS


def _floor_depth(H=200, W=120, top=0.5):
    """Synthetic: flat backdrop on top, floor receding (nearer downward) below."""
    d = np.zeros((H, W), dtype=np.float32)
    y0 = int(H * top)
    d[:y0] = 0.1                                   # far backdrop, constant
    ramp = np.linspace(0.1, 1.0, H - y0)[:, None]  # floor: closer downward
    d[y0:] = ramp
    return d


def _stacked_depth(H=200, W=120):
    """Two receding planes: a small near sliver high up (sofa seat) + a big
    dominant plane lower (the table). Dominant plane must win."""
    d = np.full((H, W), 0.1, dtype=np.float32)
    d[int(H*0.30):int(H*0.38)] = np.linspace(0.3, 0.45, int(H*0.38)-int(H*0.30))[:, None]
    y0 = int(H*0.55)
    d[y0:] = np.linspace(0.4, 1.0, H - y0)[:, None]
    return d


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    return cond


def main() -> int:
    ok = True

    # 1. flat floor: dominant band top ~= the surface start (0.5)
    a = DS._analyze_depth(_floor_depth(top=0.5))
    ok &= check("floor: band found", a["ok"])
    ok &= check(f"floor: top_frac~0.5 (got {a['top_frac']:.2f})", 0.42 <= a["top_frac"] <= 0.58)

    # 2. stacked: dominant (lower/bigger) plane wins over the near sliver
    a = DS._analyze_depth(_stacked_depth())
    ok &= check(f"stacked: picks lower plane not sliver (top {a['top_frac']:.2f})",
                a["ok"] and a["top_frac"] >= 0.45)

    # 3. degenerate solid-colour depth: no receding surface
    flat = np.full((200, 120), 0.5, dtype=np.float32)
    a = DS._analyze_depth(flat)
    ok &= check("solid: no surface signal", (not a["ok"]) or a["total_depth_span"] < 0.5)

    # 4. detect_surface never crashes when the model is unavailable -> fallback.
    #    Use a VARIED image so it passes the near-solid guard and reaches the
    #    (raising) backend, exercising the depth-failure fallback path.
    noisy = Image.fromarray(
        (np.random.RandomState(0).rand(200, 120, 3) * 255).astype(np.uint8), "RGB")
    orig = DS._get_backend
    class Boom:
        model_id = "x"
        def depth(self, img): raise RuntimeError("no torch here")
    DS._get_backend = lambda *a, **k: Boom()
    try:
        r = DS.detect_surface(noisy, fallback_frac=0.78)
    finally:
        DS._get_backend = orig
    ok &= check("no-model: used_fallback", r.used_fallback)
    ok &= check("no-model: frac==fallback", abs(r.frac - 0.78) < 1e-6)
    ok &= check("no-model: confidence 0", r.confidence == 0.0)
    ok &= check("no-model: reason mentions depth", "depth unavailable" in r.reason)

    # 4b. near-solid input falls back WITHOUT needing the model
    r = DS.detect_surface(Image.new("RGB", (120, 200), (128, 128, 128)),
                          fallback_frac=0.78)
    ok &= check("solid-input: used_fallback", r.used_fallback)
    ok &= check("solid-input: reason mentions near-solid", "near-solid" in r.reason)

    # 5. surface_y maps frac -> pixels
    r2 = DS.SurfaceResult(0.5, 0.9, False, 1.0, 0.5, "x")
    ok &= check("surface_y(1000)==500", r2.surface_y(1000) == 500)

    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
