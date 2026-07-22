"""V2 orchestrator — one transparent PNG + a scene prompt -> composited product shot.

Pipeline (Phase 1):
  1. load config, validate the product PNG has real transparency (fail fast)
  2. build the background prompt from scene.json
  3. ComfyUI: generate an empty 9:16 background (bg_generate graph)
  4. surface: detect the contact line FROM the generated background via a depth
     map (Phase 3); fall back to config surface_line_frac on low confidence
  5. geometry: tight-crop product, fit into target box, place base on that
     contact line, derive the contact shadow
  6. ComfyUI: composite shadow-then-product onto the background (composite graph)

Run inside a Python env that has Pillow (e.g. the ComfyUI venv):
    python scripts/generate.py --server 127.0.0.1:8188
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geometry as G
import prompt_builder as PB
import analyze_product_light as AL
import detect_surface as DS
import shadow as SH
from comfy_client import ComfyClient, ComfyUIError

# Phase 7 swap backend: how many px to erode the product alpha to kill the
# cut-out halo before compositing. align/cv2 are imported lazily inside the
# swap branch so the other backends stay opencv-free.
SWAP_DEFRINGE_PX = 3

# Phase 7 "B" edge treatment (light-wrap), done in PIL before the ComfyUI
# composite — same division of labour as bake_shadow. Product INTERIOR pixels
# are never touched; only a thin rim band along the edge gets scene light
# screened in, plus a soft alpha feather for a seamless paste. Live-calibrated
# on the basket scene (task 6). rim/strength wider+stronger reads more "melted
# in"; too much and the edge glows.
SWAP_LW_RIM_PX = 7        # width of the rim band the wrap affects
SWAP_LW_STRENGTH = 0.28   # how strongly scene light screens onto the rim (0..1)
SWAP_LW_FEATHER_PX = 0.0  # alpha-edge softening; >0 smears a bright halo where
                          # the scene behind the edge is bright, so keep it off —
                          # defringe already gives a clean edge (task 6 calibration)

ROOT = Path(__file__).resolve().parent.parent


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def inject_background(graph: dict, positive: str, gen: dict, seed: int) -> None:
    graph["57:27"]["inputs"]["text"] = positive
    graph["57:13"]["inputs"]["width"] = int(gen["width"])
    graph["57:13"]["inputs"]["height"] = int(gen["height"])
    ks = graph["57:3"]["inputs"]
    ks["seed"] = int(seed)
    ks["steps"] = int(gen["steps"])
    ks["cfg"] = float(gen["cfg"])
    ks["sampler_name"] = str(gen["sampler"])
    ks["scheduler"] = str(gen.get("scheduler", "simple"))


def inject_composite(graph: dict, bg_name: str, product_name: str, g: G.Geometry,
                     filename_prefix: str) -> None:
    # The contact shadow is baked into the background in Python (bake_shadow)
    # BEFORE upload, so the graph only has to drop the product onto it.
    graph["80"]["inputs"]["image"] = bg_name            # LoadImage background (+shadow)
    graph["63"]["inputs"]["image"] = product_name       # LoadImage product (cropped)
    graph["65"]["inputs"]["width"] = g.product_w        # product ImageScale
    graph["65"]["inputs"]["height"] = g.product_h
    graph["69"]["inputs"]["x"] = g.product_x            # product composite
    graph["69"]["inputs"]["y"] = g.product_y
    graph["9"]["inputs"]["filename_prefix"] = filename_prefix


def bake_shadow(bg_path: Path, g: G.Geometry, out_path: Path) -> Path:
    """Composite the elliptical radial-gradient contact shadow onto the
    generated background (Phase 5). Runs before the product is placed, so the
    product will sit on top of its own shadow. Pure PIL — the sticker's alpha
    gradient composites cleanly, no ComfyUI mask plumbing."""
    bg = Image.open(bg_path).convert("RGBA")
    sticker = SH.radial_shadow(
        g.shadow_w, g.shadow_h, opacity=g.shadow_opacity,
        falloff=g.shadow_falloff, core_frac=g.shadow_core_frac,
        feather=g.shadow_feather)
    layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    layer.paste(sticker, (g.shadow_x, g.shadow_y), sticker)
    out = Image.alpha_composite(bg, layer).convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)
    return out_path


def bake_light_wrap(product: Image.Image, scene: Image.Image, x: int, y: int,
                    rim_px: int = SWAP_LW_RIM_PX, strength: float = SWAP_LW_STRENGTH,
                    feather_px: float = SWAP_LW_FEATHER_PX) -> Image.Image:
    """Phase 7 "B": edge-feather + light-wrap the (already final-size) product
    against the scene it will be dropped into, in pure PIL. The product's ambient
    surroundings are sampled, blurred, and SCREENED onto a thin rim band just
    inside the alpha edge — so the scene's light appears to wrap the product
    silhouette. The interior (rim mask == 0) is left byte-for-byte; only the
    outer edge changes. The alpha edge is also softened for a seamless composite.
    rim_px/strength/feather_px are live-calibrated. strength<=0 disables the wrap
    (feather still applies)."""
    w, h = product.size
    prod = product.convert("RGBA")
    a = prod.getchannel("A")
    rgb = prod.convert("RGB")

    if strength > 0 and rim_px > 0:
        # ambient light under/around the product's footprint (crop stays w x h;
        # PIL zero-pads if the product spills past the scene edge — negligible)
        region = scene.convert("RGB").crop((x, y, x + w, y + h))
        if region.size != (w, h):
            region = region.resize((w, h))
        blur = region.filter(ImageFilter.GaussianBlur(max(w, h) * 0.06))
        # rim = alpha minus its erosion -> a ring hugging the edge, then feathered
        inner = a.filter(ImageFilter.MinFilter(2 * rim_px + 1))
        rim = ImageChops.subtract(a, inner).filter(ImageFilter.GaussianBlur(feather_px))
        rim = rim.point(lambda v: int(v * strength))
        screened = ImageChops.screen(rgb, blur)
        rgb = Image.composite(screened, rgb, rim)

    a2 = a.filter(ImageFilter.GaussianBlur(feather_px)) if feather_px > 0 else a
    out = rgb.convert("RGBA")
    out.putalpha(a2)
    return out


def resolve_surface(bg_path, scene_cfg: dict, args) -> float:
    """Pick the contact-line fraction. Precedence:
      1. --surface-line-frac  (MANUAL override, highest)
      2. --fixed-surface      (use scene.json value, skip detection)
      3. auto-detect from the background via depth (Phase 3), falling back to
         the config value on low confidence / tilt / missing model."""
    manual = getattr(args, "surface_line_frac", None)
    if manual is not None:
        print(f"surface : MANUAL -> {float(manual):.3f}")
        return float(manual)
    fixed = float(scene_cfg["surface_line_frac"])
    if getattr(args, "fixed_surface", False):
        print(f"surface : fixed (config) -> {fixed:.3f}")
        return fixed
    r = DS.detect_surface(bg_path, fallback_frac=fixed,
                          min_confidence=args.surface_min_conf)
    tag = "FALLBACK" if r.used_fallback else "auto"
    print(f"surface : {tag} -> {r.frac:.3f} (conf={r.confidence:.2f}) :: {r.reason}")
    return r.frac


def effective_overrides(product_cfg: dict, args) -> dict:
    """config overrides (product.json) with any MANUAL CLI knobs layered on top."""
    ov = dict(product_cfg.get("overrides", {}))
    for key in ("offset_x", "offset_y", "scale_mult"):
        val = getattr(args, key, None)
        if val is not None:
            ov[key] = val
    return ov


def resolve_backend(gen: dict, args, root: Path):
    """Pick the background backend and (for manual/swap) the image path.
    Precedence: --scene wins and implies swap; --bg wins and implies manual;
    else config `backend`.
      - comfyui: generate the background with ComfyUI (returns path None)
      - manual : use a ready-made empty background (MJ/GPT/photo); we bake the
                 shadow and composite the product (Phase 6)
      - swap   : use a GPT-generated FULL scene (product already in it) as the
                 template; align + brush the real product back over the fake one,
                 inheriting the scene's shadow/light (Phase 7)
    Returns (backend, path). Raises ValueError if manual/swap has no image."""
    if getattr(args, "scene", None) is not None:
        return "swap", Path(args.scene)
    if getattr(args, "bg", None) is not None:
        return "manual", Path(args.bg)
    backend = str(gen.get("backend", "comfyui")).strip().lower()
    if backend == "manual":
        mp = gen.get("manual_bg_path")
        if not mp:
            raise ValueError(
                "backend 'manual' needs a background image: pass --bg <path> "
                "or set generation.json manual_bg_path")
        p = Path(mp)
        return "manual", (p if p.is_absolute() else root / p)
    if backend == "swap":
        sp = gen.get("scene_path")
        if not sp:
            raise ValueError(
                "backend 'swap' needs a full GPT scene image: pass --scene <path> "
                "or set generation.json scene_path")
        p = Path(sp)
        return "swap", (p if p.is_absolute() else root / p)
    return "comfyui", None


def frame_from_background(bg_path: Path) -> tuple[int, int]:
    """Read a manual background's ACTUAL pixel size to use as the frame — the
    pipeline (geometry / composite) works relative to this, so any aspect ratio
    runs (Phase 6). Warns if it isn't ~9:16 but does NOT crop or resize."""
    with Image.open(bg_path) as im:
        w, h = im.size
    ratio = w / h
    target = 9 / 16
    if abs(ratio - target) > 0.02:
        print(f"⚠️  background is {w}x{h} ({ratio:.3f}), not 9:16 ({target:.3f}). "
              f"Output will be this aspect; crop it yourself first if you want 9:16.")
    return w, h


def resolve_shadow_dir(backend: str, args, profile) -> str:
    """Where the cast shadow falls. --shadow-dir wins in BOTH modes; else manual
    defaults to 'right' (no product-light analysis there), comfyui uses the
    product-light analysis (Phase 2)."""
    cli = getattr(args, "shadow_dir", None)
    if cli is not None:
        return cli
    if backend == "manual":
        return "right"
    return profile.shadow_dir


def build_geometry(crop, frame_w, frame_h, product_cfg: dict, surface_frac: float,
                   overrides: dict, shadow_dir: str) -> G.Geometry:
    return G.compute(crop.width, crop.height, frame_w, frame_h,
                     product_cfg["target_box"], surface_frac, overrides, shadow_dir)


def print_geometry(g: G.Geometry, product_path: Path, shadow_dir) -> None:
    print(f"product : {product_path.name} -> {g.product_w}x{g.product_h} "
          f"@({g.product_x},{g.product_y})  base@{g.product_y + g.product_h} "
          f"(surface {g.surface_y})  shadow_dir={shadow_dir}")
    if g.shadow_w > 0:  # swap bakes no shadow -> nothing to report
        print(f"shadow  : sticker {g.shadow_w}x{g.shadow_h}@({g.shadow_x},{g.shadow_y}) "
              f"op{g.shadow_opacity} falloff{g.shadow_falloff} core{g.shadow_core_frac}")


def swap_geometry(scene_path: Path, crop, overrides: dict) -> G.Geometry:
    """Phase 7: locate GPT's rendered product in the scene and build the
    Geometry that drops the real product over it (align + force-cover)."""
    import align as A
    r = A.locate_product(scene_path, crop)
    print(f"align   : GPT product bbox={r.bbox} score={r.score:.3f} scale={r.scale:.3f}")
    return A.build_swap_geometry(r, overrides)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="V2 product scene compositor")
    ap.add_argument("--root", default=str(ROOT), help="project root")
    ap.add_argument("--server", default="127.0.0.1:8188", help="ComfyUI host:port")
    ap.add_argument("--product", default=None, help="override product_image path")
    # --- Phase 6: background backend ---
    ap.add_argument("--bg", default=None,
                    help="use a ready-made EMPTY background image (MJ/GPT/photo); "
                         "implies manual backend, skips ComfyUI generation")
    ap.add_argument("--scene", default=None,
                    help="use a GPT-generated FULL scene (product already in it) as "
                         "a template; implies swap backend — align + brush the real "
                         "product back over the fake one, inheriting its shadow/light")
    ap.add_argument("--shadow-dir", dest="shadow_dir", default=None,
                    choices=["left", "right", "none"],
                    help="cast-shadow direction; overrides product-light analysis "
                         "(manual backend defaults to right)")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate + geometry only, no ComfyUI calls")
    ap.add_argument("--fixed-surface", action="store_true",
                    help="skip depth detection; use scene.json surface_line_frac")
    ap.add_argument("--surface-min-conf", type=float, default=0.45,
                    help="min detection confidence before falling back to config")
    # --- manual correction knobs (override auto detection / config) ---
    #     auto detection is only ~70-80% right; these let a human nudge the
    #     result without editing config. Any given flag wins over auto/config.
    ap.add_argument("--surface-line-frac", type=float, default=None,
                    help="MANUAL contact line (0..1); overrides auto detection")
    ap.add_argument("--offset-x", type=int, default=None,
                    help="MANUAL horizontal nudge in px (+right)")
    ap.add_argument("--offset-y", type=int, default=None,
                    help="MANUAL vertical nudge in px (+down)")
    ap.add_argument("--scale-mult", type=float, default=None,
                    help="MANUAL scale multiplier on the fitted product size")
    args = ap.parse_args(argv)
    root = Path(args.root)

    product_cfg = load_json(root / "config" / "product.json")
    scene_cfg = load_json(root / "config" / "scene.json")
    gen = load_json(root / "config" / "generation.json")

    product_path = Path(args.product or (root / product_cfg["product_image"]))

    # --- pick the background backend (--scene > --bg > config) ---
    try:
        backend, bg_src = resolve_backend(gen, args, root)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # swap inherits shadow/light from the GPT scene, so --shadow-dir is moot
    if backend == "swap" and getattr(args, "shadow_dir", None) is not None:
        print("⚠️  --shadow-dir is ignored in swap backend "
              "(shadow comes from the GPT scene)")

    # --- fail fast: reject non-transparent input BEFORE touching ComfyUI ---
    try:
        product_img = G.load_transparent_png(product_path)
    except (G.NoAlphaError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # --- product-led lighting (comfyui only): analyze the product, drive the bg
    #     prompt. In manual mode the background is already made, so we skip this
    #     (nothing to prompt) — Phase 6 decision #4. ---
    profile = None
    positive = None
    if backend == "comfyui":
        profile = AL.analyze(product_img)
        scene_render = dict(scene_cfg)
        if str(scene_cfg.get("lighting", "")).strip().lower() == "auto":
            scene_render["lighting"] = profile.lighting_clause()
            print(f"lighting: AUTO from product -> {profile.lighting_clause()}")
        else:
            print(f"lighting: manual (scene.json) -> {scene_cfg.get('lighting')}")
        positive, _negative = PB.load_prompts(root, scene_render)
        frame_w, frame_h = int(gen["width"]), int(gen["height"])
    else:  # manual / swap: the ready-made image's ACTUAL size is the frame
        if not bg_src.exists():
            kind = "scene" if backend == "swap" else "background"
            print(f"ERROR: {kind} image not found: {bg_src}", file=sys.stderr)
            return 2
        print(f"backend : {backend} -> {bg_src}")
        frame_w, frame_h = frame_from_background(bg_src)

    # swap places the product by matching GPT's rendered product (align), so it
    # never casts/bakes a shadow — leave shadow_dir out of it entirely.
    shadow_dir = None if backend == "swap" else resolve_shadow_dir(backend, args, profile)

    # --- tight-crop the product now (needed for both geometry and upload).
    #     The contact-surface line is resolved LATER, once the background
    #     exists, so depth detection can adapt to it (Phase 3). ---
    crop = G.tight_crop(product_img)
    if backend == "swap":
        # kill the cut-out halo so it doesn't show against GPT's scene (Phase 7)
        crop = G.defringe(crop, SWAP_DEFRINGE_PX)
    cropped = root / "outputs" / "composites" / "_product_cropped.png"
    cropped.parent.mkdir(parents=True, exist_ok=True)
    crop.save(cropped)

    eff_ov = effective_overrides(product_cfg, args)

    if args.dry_run:
        if backend == "swap":
            # align needs no ComfyUI, so it runs in dry-run too
            g = swap_geometry(bg_src, crop, eff_ov)
            print_geometry(g, product_path, "n/a (swap)")
        else:
            # no depth pass in dry-run -> manual line if given, else config line
            if args.surface_line_frac is not None:
                frac = float(args.surface_line_frac)
                print(f"surface : MANUAL -> {frac:.3f}")
            else:
                frac = float(scene_cfg["surface_line_frac"])
                print(f"surface : dry-run uses config -> {frac:.3f}")
            g = build_geometry(crop, frame_w, frame_h, product_cfg, frac, eff_ov,
                               shadow_dir)
            print_geometry(g, product_path, shadow_dir)
        print(f"dry-run: skipping ComfyUI. backend={backend}, "
              f"frame={frame_w}x{frame_h}. geometry OK.")
        return 0

    # composite runs on ComfyUI in BOTH backends, so we need the server either way
    client = ComfyClient(args.server)
    if not client.ping():
        print(f"ERROR: cannot reach ComfyUI at {args.server}. Is it running?",
              file=sys.stderr)
        return 3

    try:
        if backend == "swap":
            # --- Phase 7: GPT scene IS the background (product already in it);
            #     locate it, then brush the real product over the same spot.
            #     No depth, no bake_shadow, no lighting — all inherited. ---
            g = swap_geometry(bg_src, crop, eff_ov)
            print_geometry(g, product_path, "n/a (swap)")
            # "B": light-wrap the product against the scene (PIL), then let the
            # ComfyUI composite paste it. Bake at the FINAL size so node 65's
            # rescale is a no-op and the wrap aligns with the paste position.
            scene_img = Image.open(bg_src).convert("RGBA")
            prod_final = crop.resize((g.product_w, g.product_h), Image.LANCZOS)
            wrapped = bake_light_wrap(prod_final, scene_img, g.product_x, g.product_y)
            wrapped.save(cropped)
            print(f"lightwrap: rim{SWAP_LW_RIM_PX} strength{SWAP_LW_STRENGTH} "
                  f"feather{SWAP_LW_FEATHER_PX}")
            bg_out = bg_src
        else:
            # --- Stage 1: obtain the background ---
            if backend == "comfyui":
                bg_graph = load_json(root / "workflows" / "comfyui_api" / "bg_generate_api.json")
                seed = random.randint(0, 2**63 - 1) if int(gen["seed"]) < 0 else int(gen["seed"])
                print(f"seed    : {seed}")
                inject_background(bg_graph, positive, gen, seed)
                bg_out = root / gen.get("bg_output_path", "outputs/backgrounds/background.png")
                bg_bytes = client.run(bg_graph, save_to=bg_out)
                if not bg_bytes:
                    print("ERROR: background stage produced no image", file=sys.stderr)
                    return 4
                print(f"background saved -> {bg_out}")
            else:  # manual: the ready-made image IS the background (left untouched)
                bg_out = bg_src

            # --- Phase 3: resolve the contact surface FROM the background,
            #     then compute geometry against it ---
            frac = resolve_surface(bg_out, scene_cfg, args)
            g = build_geometry(crop, frame_w, frame_h, product_cfg, frac, eff_ov,
                               shadow_dir)
            print_geometry(g, product_path, shadow_dir)

            # --- Phase 5: bake the contact shadow into the bg before upload ---
            bg_shadowed = root / "outputs" / "composites" / "_bg_with_shadow.png"
            bake_shadow(bg_out, g, bg_shadowed)
            bg_out = bg_shadowed

        # --- Stage 2: composite the product onto the (shadowed | GPT) background.
        #     comfyui/manual pre-baked the shadow into bg_out; swap uses the raw
        #     GPT scene. Same composite graph either way. ---
        bg_name = client.upload_image(bg_out)
        product_name = client.upload_image(cropped)
        comp_graph = load_json(root / "workflows" / "comfyui_api" / "composite_api.json")
        inject_composite(comp_graph, bg_name, product_name, g, "product_scene_v2")
        final_out = root / gen.get("output_path", "outputs/final/final.png")
        client.run(comp_graph, save_to=final_out)
        print(f"final saved -> {final_out}")
    except ComfyUIError as e:
        print(f"ERROR: ComfyUI: {e}", file=sys.stderr)
        return 4

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
