"""V2 orchestrator — one transparent PNG + a scene prompt -> composited product shot.

Pipeline (Phase 1):
  1. load config, validate the product PNG has real transparency (fail fast)
  2. build the background prompt from scene.json
  3. ComfyUI: generate an empty 9:16 background (bg_generate graph)
  4. geometry: tight-crop product, fit into target box, place base on the
     contact line (config surface_line_frac), derive the contact shadow
  5. ComfyUI: composite shadow-then-product onto the background (composite graph)

Run inside a Python env that has Pillow (e.g. the ComfyUI venv):
    python scripts/generate.py --server 127.0.0.1:8188
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geometry as G
import prompt_builder as PB
import analyze_product_light as AL
from comfy_client import ComfyClient, ComfyUIError

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
    graph["80"]["inputs"]["image"] = bg_name            # LoadImage background
    graph["63"]["inputs"]["image"] = product_name       # LoadImage product (cropped)
    graph["65"]["inputs"]["width"] = g.product_w        # product ImageScale
    graph["65"]["inputs"]["height"] = g.product_h
    graph["69"]["inputs"]["x"] = g.product_x            # product composite
    graph["69"]["inputs"]["y"] = g.product_y
    graph["73"]["inputs"]["width"] = g.shadow_w         # shadow flatten
    graph["73"]["inputs"]["height"] = g.shadow_h
    graph["74"]["inputs"]["blur_radius"] = g.shadow_blur  # shadow blur
    graph["76"]["inputs"]["value"] = g.shadow_opacity   # shadow opacity
    graph["76"]["inputs"]["width"] = g.shadow_w
    graph["76"]["inputs"]["height"] = g.shadow_h
    graph["78"]["inputs"]["width"] = g.shadow_w         # shadow color canvas
    graph["78"]["inputs"]["height"] = g.shadow_h
    graph["79"]["inputs"]["x"] = g.shadow_x             # shadow composite
    graph["79"]["inputs"]["y"] = g.shadow_y
    graph["9"]["inputs"]["filename_prefix"] = filename_prefix


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="V2 product scene compositor")
    ap.add_argument("--root", default=str(ROOT), help="project root")
    ap.add_argument("--server", default="127.0.0.1:8188", help="ComfyUI host:port")
    ap.add_argument("--product", default=None, help="override product_image path")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate + geometry only, no ComfyUI calls")
    args = ap.parse_args(argv)
    root = Path(args.root)

    product_cfg = load_json(root / "config" / "product.json")
    scene_cfg = load_json(root / "config" / "scene.json")
    gen = load_json(root / "config" / "generation.json")

    product_path = Path(args.product or (root / product_cfg["product_image"]))
    frame_w, frame_h = int(gen["width"]), int(gen["height"])

    # --- fail fast: reject non-transparent input BEFORE touching ComfyUI ---
    try:
        product_img = G.load_transparent_png(product_path)
    except (G.NoAlphaError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # --- product-led lighting: analyze the product, drive the bg prompt ---
    profile = AL.analyze(product_img)
    scene_render = dict(scene_cfg)
    if str(scene_cfg.get("lighting", "")).strip().lower() == "auto":
        scene_render["lighting"] = profile.lighting_clause()
        print(f"lighting: AUTO from product -> {profile.lighting_clause()}")
    else:
        print(f"lighting: manual (scene.json) -> {scene_cfg.get('lighting')}")

    # --- geometry (shadow falls per the product's light direction) ---
    cropped = root / "outputs" / "composites" / "_product_cropped.png"
    g = G.prepare_product(
        product_path, cropped, frame_w, frame_h,
        product_cfg["target_box"], scene_cfg["surface_line_frac"],
        product_cfg.get("overrides", {}), profile.shadow_dir,
    )

    positive, _negative = PB.load_prompts(root, scene_render)
    seed = random.randint(0, 2**63 - 1) if int(gen["seed"]) < 0 else int(gen["seed"])

    print(f"product : {product_path.name} -> {g.product_w}x{g.product_h} "
          f"@({g.product_x},{g.product_y})  base@{g.product_y + g.product_h} "
          f"(surface {g.surface_y})  shadow_dir={profile.shadow_dir}")
    print(f"shadow  : {g.shadow_w}x{g.shadow_h} @({g.shadow_x},{g.shadow_y}) "
          f"opacity {g.shadow_opacity} blur {g.shadow_blur}")
    print(f"seed    : {seed}")

    if args.dry_run:
        print("dry-run: skipping ComfyUI. geometry OK.")
        return 0

    client = ComfyClient(args.server)
    if not client.ping():
        print(f"ERROR: cannot reach ComfyUI at {args.server}. Is it running?",
              file=sys.stderr)
        return 3

    try:
        # --- Stage 1: background ---
        bg_graph = load_json(root / "workflows" / "comfyui_api" / "bg_generate_api.json")
        inject_background(bg_graph, positive, gen, seed)
        bg_out = root / gen.get("bg_output_path", "outputs/backgrounds/background.png")
        bg_bytes = client.run(bg_graph, save_to=bg_out)
        if not bg_bytes:
            print("ERROR: background stage produced no image", file=sys.stderr)
            return 4
        print(f"background saved -> {bg_out}")

        # --- Stage 2: composite ---
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
