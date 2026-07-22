"""Unit tests for the Phase 7 swap alignment + edge treatment:
  - align.locate_product recovers a known product placement in a synthetic scene
  - align.build_swap_geometry applies knobs + force-cover, zeroes the shadow
  - geometry.defringe erodes alpha without touching RGB
  - generate.bake_light_wrap leaves the interior untouched, keeps size

Self-contained: the "scene" is synthesised by pasting a textured template at a
known (x, y, scale), so nothing depends on the real GPT/basket assets. Needs
opencv (swap-only dep). Run with the ComfyUI .venv python:
    python tests/test_align.py
"""
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import align as A
import geometry as G
import generate as GEN


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    return bool(cond)


def make_template(w=200, h=160) -> Image.Image:
    """A textured, ellipse-alpha product: stripes + a mark give the matcher
    something to lock onto; corners are transparent (like a real cut-out)."""
    alpha = Image.new("L", (w, h), 0)
    ImageDraw.Draw(alpha).ellipse([10, 10, w - 10, h - 10], fill=255)
    rgb = Image.new("RGB", (w, h), (180, 140, 90))
    d = ImageDraw.Draw(rgb)
    for i in range(0, w, 12):
        d.line([(i, 0), (i, h)], fill=(110, 80, 45), width=4)
    d.rectangle([70, 50, 130, 110], fill=(60, 40, 20))
    p = rgb.convert("RGBA")
    p.putalpha(alpha)
    return p


def main() -> int:
    ok = True
    tmpl = make_template()

    # --- synthesise a scene with the product at a KNOWN place/scale ---
    # A TEXTURED background matters: a flat fill lets a big up-scaled template
    # correlate spuriously with empty regions and win at the scale ceiling. Real
    # GPT scenes are textured, so give the test scene texture too.
    scale, X, Y = 1.3, 250, 400
    pw, ph = round(200 * scale), round(160 * scale)
    scene = Image.new("RGBA", (800, 1000), (210, 205, 198, 255))
    sd = ImageDraw.Draw(scene)
    for i in range(0, 1000, 9):          # horizontal weave
        sd.line([(0, i), (800, i)], fill=(190, 188, 182, 255), width=2)
    for j in range(0, 800, 37):          # sparse verticals -> breaks flatness
        sd.line([(j, 0), (j, 1000)], fill=(170, 172, 178, 255), width=1)
    scene.alpha_composite(tmpl.resize((pw, ph), Image.LANCZOS), (X, Y))

    with tempfile.TemporaryDirectory() as td:
        scene_path = Path(td) / "scene.png"
        scene.convert("RGB").save(scene_path)

        r = A.locate_product(scene_path, tmpl)
        # centre + size should match where we pasted (matcher preserves aspect)
        cx_err = abs((r.x + r.w / 2) - (X + pw / 2))
        cy_err = abs((r.y + r.h / 2) - (Y + ph / 2))
        ok &= check(f"locate centre within 12px (dx~{cx_err:.0f},dy~{cy_err:.0f})",
                    cx_err <= 12 and cy_err <= 12)
        ok &= check(f"locate scale ~1.3 (got {r.scale:.2f})", abs(r.scale - scale) <= 0.12)
        ok &= check("locate does NOT lock a tiny wrong region",
                    r.w > pw * 0.8 and r.h > ph * 0.8)

    # --- build_swap_geometry: knobs + force-cover + zeroed shadow ---
    res = A.AlignResult(x=100, y=200, w=600, h=500, score=0.5, scale=1.0)
    g0 = A.build_swap_geometry(res, cover_margin=0.0)
    ok &= check("no-margin keeps matched size", g0.product_w == 600 and g0.product_h == 500)
    gc = A.build_swap_geometry(res)  # default 3% cover
    ok &= check("force-cover scales up ~3%", gc.product_w == 618 and gc.product_h == 515)
    ok &= check("force-cover stays centred over the fake",
                abs((gc.product_x + gc.product_w / 2) - (res.x + res.w / 2)) < 1)
    gk = A.build_swap_geometry(res, {"scale_mult": 1.1, "offset_x": 20, "offset_y": -10},
                               cover_margin=0.0)
    ok &= check("scale_mult knob applies", gk.product_w == 660 and gk.product_h == 550)
    ok &= check("offset knobs shift centre",
                abs((gk.product_x + gk.product_w / 2) - (res.x + res.w / 2 + 20)) < 1 and
                abs((gk.product_y + gk.product_h / 2) - (res.y + res.h / 2 - 10)) < 1)
    ok &= check("swap geometry zeroes the shadow", gc.shadow_w == 0 and gc.shadow_opacity == 0.0)

    # --- geometry.defringe: erode alpha, leave RGB ---
    a_before = sum(tmpl.getchannel("A").point(lambda v: 1 if v > 0 else 0).getdata())
    d2 = G.defringe(tmpl, 2)
    a_after = sum(d2.getchannel("A").point(lambda v: 1 if v > 0 else 0).getdata())
    ok &= check("defringe shrinks opaque area", a_after < a_before)
    ok &= check("defringe leaves RGB untouched",
                list(tmpl.convert("RGB").getdata()) == list(d2.convert("RGB").getdata()))
    ok &= check("defringe(0) is a no-op",
                list(G.defringe(tmpl, 0).getchannel("A").getdata()) ==
                list(tmpl.getchannel("A").getdata()))

    # --- bake_light_wrap: interior untouched, size preserved ---
    prod = tmpl.resize((pw, ph), Image.LANCZOS)
    wrapped = GEN.bake_light_wrap(prod, scene, X, Y)
    ok &= check("light-wrap keeps size", wrapped.size == prod.size)
    cx, cy = pw // 2, ph // 2  # deep interior pixel (rim mask == 0 there)
    ok &= check("light-wrap leaves the interior byte-for-byte",
                wrapped.convert("RGB").getpixel((cx, cy)) == prod.convert("RGB").getpixel((cx, cy)))
    off = GEN.bake_light_wrap(prod, scene, X, Y, strength=0.0, feather_px=0.0)
    ok &= check("light-wrap strength=0,feather=0 -> RGB identical",
                list(off.convert("RGB").getdata()) == list(prod.convert("RGB").getdata()))

    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
