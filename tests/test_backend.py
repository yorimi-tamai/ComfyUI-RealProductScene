"""Unit tests for the Phase 6 background-backend logic in generate.py:
backend resolution (--bg > config, manual needs an image), manual-background
actual-size framing, and shadow_dir source (--shadow-dir > manual-default >
product analysis). Offline, no ComfyUI.
Run with the ComfyUI .venv python:  python tests/test_backend.py
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import generate as GEN


def args(**kw):
    base = dict(bg=None, scene=None, shadow_dir=None)
    base.update(kw)
    return SimpleNamespace(**base)


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    return bool(cond)


def main() -> int:
    ok = True
    root = Path("/proj")

    # --- resolve_backend precedence ---
    b, p = GEN.resolve_backend({"backend": "comfyui"}, args(), root)
    ok &= check("config comfyui -> comfyui, no path", b == "comfyui" and p is None)

    b, p = GEN.resolve_backend(
        {"backend": "manual", "manual_bg_path": "inputs/refs/x.png"}, args(), root)
    ok &= check("config manual + path -> manual, root-relative",
                b == "manual" and p == root / "inputs/refs/x.png")

    b, p = GEN.resolve_backend(
        {"backend": "manual", "manual_bg_path": "/abs/x.png"}, args(), root)
    ok &= check("config manual + absolute path kept",
                b == "manual" and p == Path("/abs/x.png"))

    raised = False
    try:
        GEN.resolve_backend({"backend": "manual", "manual_bg_path": None}, args(), root)
    except ValueError:
        raised = True
    ok &= check("config manual + no path -> ValueError", raised)

    b, p = GEN.resolve_backend(
        {"backend": "manual", "manual_bg_path": "cfg.png"},
        args(bg="/cli/hero.png"), root)
    ok &= check("--bg beats config path", b == "manual" and p == Path("/cli/hero.png"))

    b, _ = GEN.resolve_backend({"backend": "comfyui"}, args(bg="/cli/hero.png"), root)
    ok &= check("--bg beats config comfyui", b == "manual")

    b, _ = GEN.resolve_backend({}, args(), root)
    ok &= check("missing backend key -> comfyui default", b == "comfyui")

    # --- Phase 7: swap backend (--scene > --bg > config) ---
    b, p = GEN.resolve_backend({"backend": "comfyui"}, args(scene="/cli/full.png"), root)
    ok &= check("--scene implies swap", b == "swap" and p == Path("/cli/full.png"))

    b, p = GEN.resolve_backend(
        {"backend": "swap", "scene_path": "inputs/refs/s.png"}, args(), root)
    ok &= check("config swap + scene_path -> swap, root-relative",
                b == "swap" and p == root / "inputs/refs/s.png")

    b, _ = GEN.resolve_backend({"backend": "comfyui"},
                               args(scene="/s.png", bg="/b.png"), root)
    ok &= check("--scene beats --bg", b == "swap")

    raised = False
    try:
        GEN.resolve_backend({"backend": "swap"}, args(), root)
    except ValueError:
        raised = True
    ok &= check("config swap + no scene_path -> ValueError", raised)

    # --- frame_from_background: actual pixel size, any aspect ---
    with tempfile.TemporaryDirectory() as td:
        sq = Path(td) / "mj_1x1.png"
        Image.new("RGB", (1024, 1024), (200, 190, 180)).save(sq)
        w, h = GEN.frame_from_background(sq)  # prints a non-9:16 warning
        ok &= check("frame reads actual 1024x1024", (w, h) == (1024, 1024))

        nine = Path(td) / "nine_sixteen.png"
        Image.new("RGB", (576, 1024), (200, 190, 180)).save(nine)
        w, h = GEN.frame_from_background(nine)
        ok &= check("frame reads actual 576x1024 (9:16, no warn)", (w, h) == (576, 1024))

    # --- resolve_shadow_dir source ---
    prof = SimpleNamespace(shadow_dir="left")
    ok &= check("comfyui uses product analysis",
                GEN.resolve_shadow_dir("comfyui", args(), prof) == "left")
    ok &= check("manual defaults to right (no analysis)",
                GEN.resolve_shadow_dir("manual", args(), None) == "right")
    ok &= check("--shadow-dir overrides comfyui analysis",
                GEN.resolve_shadow_dir("comfyui", args(shadow_dir="none"), prof) == "none")
    ok &= check("--shadow-dir overrides manual default",
                GEN.resolve_shadow_dir("manual", args(shadow_dir="left"), None) == "left")

    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
