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


def _ambiguous_stack_depth(H=200, W=120):
    """Two COMPARABLY sized receding planes separated by a gap: a table top
    (upper) and the floor seen through/around it (lower). Neither dominates —
    a centred product could rest on either — so detection must fall back rather
    than gamble on one (Phase 5 #2)."""
    d = np.full((H, W), 0.1, dtype=np.float32)
    y0, y1 = int(H*0.30), int(H*0.50)      # upper plane, extent ~0.20H
    d[y0:y1] = np.linspace(0.30, 0.60, y1 - y0)[:, None]
    y2, y3 = int(H*0.62), int(H*0.85)      # lower plane, extent ~0.23H (comparable)
    d[y2:y3] = np.linspace(0.55, 1.00, y3 - y2)[:, None]
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

    # 2. stacked: dominant (lower/bigger) plane wins over the near sliver, and a
    #    small sliver does NOT trip the ambiguity gate (runner-up stays low)
    a = DS._analyze_depth(_stacked_depth())
    ok &= check(f"stacked: picks lower plane not sliver (top {a['top_frac']:.2f})",
                a["ok"] and a["top_frac"] >= 0.45)
    ok &= check(f"stacked-sliver: runner-up low (got {a['runner_up_ratio']:.2f})",
                a["runner_up_ratio"] < 0.70)

    # 2b. ambiguous stack (comparable planes / glass see-through): high runner-up
    a = DS._analyze_depth(_ambiguous_stack_depth())
    ok &= check(f"ambiguous: runner-up ratio high (got {a['runner_up_ratio']:.2f})",
                a["ok"] and a["runner_up_ratio"] >= 0.70)
    #     and detect_surface must FALL BACK on it (model mocked to emit that depth)
    noisy2 = Image.fromarray(
        (np.random.RandomState(1).rand(200, 120, 3) * 255).astype(np.uint8), "RGB")
    dep = _ambiguous_stack_depth()
    orig_b = DS._get_backend
    class FakeDepth:
        model_id = "x"
        def depth(self, img): return dep
    DS._get_backend = lambda *a, **k: FakeDepth()
    try:
        r = DS.detect_surface(noisy2, fallback_frac=0.78)
    finally:
        DS._get_backend = orig_b
    ok &= check("ambiguous: used_fallback", r.used_fallback)
    ok &= check("ambiguous: reason mentions ambiguous", "ambiguous" in r.reason)

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

    # 5. adaptive front_k: monotonic in span, clamped to [0.5, 0.8], bigger
    #    span -> product pushed further toward the near edge (Phase 5 #5)
    ks = [DS.adaptive_front_k(s) for s in (0.0, 0.15, 0.30, 0.50, 0.80)]
    ok &= check("adaptive_k monotonic non-decreasing",
                all(b >= a - 1e-9 for a, b in zip(ks, ks[1:])))
    ok &= check(f"adaptive_k within [0.5,0.8] (got {min(ks):.2f}..{max(ks):.2f})",
                min(ks) >= 0.5 and max(ks) <= 0.8)
    ok &= check("adaptive_k: bigger span -> bigger k",
                DS.adaptive_front_k(0.5) > DS.adaptive_front_k(0.1))

    # 6. surface_y maps frac -> pixels
    r2 = DS.SurfaceResult(0.5, 0.9, False, 1.0, 0.5, "x")
    ok &= check("surface_y(1000)==500", r2.surface_y(1000) == 500)

    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
