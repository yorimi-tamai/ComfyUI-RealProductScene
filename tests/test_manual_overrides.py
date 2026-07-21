"""Unit tests for the manual-correction interface in generate.py:
override precedence (manual > fixed > auto) and override layering.
Run with the ComfyUI .venv python:  python tests/test_manual_overrides.py
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import generate as GEN
import detect_surface as DS


def args(**kw):
    base = dict(surface_line_frac=None, fixed_surface=False, surface_min_conf=0.45,
                offset_x=None, offset_y=None, scale_mult=None)
    base.update(kw)
    return SimpleNamespace(**base)


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    return cond


def main() -> int:
    ok = True
    scene = {"surface_line_frac": 0.78}

    # --- resolve_surface precedence ---
    # 1. manual wins over everything (no model call)
    f = GEN.resolve_surface("unused.png", scene, args(surface_line_frac=0.62))
    ok &= check("manual overrides all -> 0.62", abs(f - 0.62) < 1e-9)

    # 2. fixed-surface uses config, skips detection
    f = GEN.resolve_surface("unused.png", scene, args(fixed_surface=True))
    ok &= check("fixed-surface -> config 0.78", abs(f - 0.78) < 1e-9)

    # 3. auto path calls detect_surface (monkeypatched)
    orig = DS.detect_surface
    DS.detect_surface = lambda *a, **k: DS.SurfaceResult(
        0.55, 0.9, False, 1.0, 0.55, "stub auto")
    try:
        f = GEN.resolve_surface("unused.png", scene, args())
    finally:
        DS.detect_surface = orig
    ok &= check("auto path -> detected 0.55", abs(f - 0.55) < 1e-9)

    # 4. manual beats fixed if both set
    f = GEN.resolve_surface("unused.png", scene,
                            args(surface_line_frac=0.4, fixed_surface=True))
    ok &= check("manual beats fixed -> 0.40", abs(f - 0.40) < 1e-9)

    # --- effective_overrides layering ---
    pcfg = {"overrides": {"offset_x": 5, "offset_y": 0, "scale_mult": 1.0,
                          "shadow_opacity": 0.3}}
    ov = GEN.effective_overrides(pcfg, args())
    ok &= check("no CLI -> config kept", ov["offset_x"] == 5 and ov["scale_mult"] == 1.0)
    ok &= check("config-only key survives", ov["shadow_opacity"] == 0.3)

    ov = GEN.effective_overrides(pcfg, args(offset_x=40, scale_mult=1.25))
    ok &= check("CLI overrides config", ov["offset_x"] == 40 and ov["scale_mult"] == 1.25)
    ok &= check("unset CLI keeps config", ov["offset_y"] == 0)
    ok &= check("CLI does not drop config-only key", ov["shadow_opacity"] == 0.3)

    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
