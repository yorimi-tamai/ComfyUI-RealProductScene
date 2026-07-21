"""Node A — AnalyzeProductLighting (pre-generation).

Reads the product's lighting and builds the background prompt so the generated
scene MATCHES the product (product-led lighting, Phase 2). Runs BEFORE the
KSampler: its positive_prompt output feeds CLIP Text Encode.

Wraps the shared brain (analyze_product_light + prompt_builder) — no logic is
duplicated here. The product enters as IMAGE + MASK and is rebuilt to RGBA;
a non-cut-out input raises a clear error (same guard as the CLI).
"""

from __future__ import annotations

import sys
from pathlib import Path

from . import tensor_io as TIO  # also puts ../scripts on sys.path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import analyze_product_light as AL  # noqa: E402
import prompt_builder as PB  # noqa: E402

# scene.json defaults, surfaced as widget defaults so the node is usable as-is
_DEF = {
    "scene": "modern minimalist living room",
    "visual_style": "high-end commercial product photography",
    "camera": "eye-level medium shot",
    "reserved_space": ("clean, empty tabletop at the lower-center of the frame, "
                       "ready to place the product"),
    "manual_lighting": "soft natural light, from the upper left, balanced exposure",
}


class AnalyzeProductLighting:
    """product (IMAGE+MASK) + scene fields -> positive/negative prompt + shadow_dir."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "product_image": ("IMAGE",),
                "product_mask": ("MASK",),
                "scene": ("STRING", {"default": _DEF["scene"]}),
                "visual_style": ("STRING", {"default": _DEF["visual_style"]}),
                "camera": ("STRING", {"default": _DEF["camera"]}),
                "reserved_space": ("STRING", {"default": _DEF["reserved_space"],
                                              "multiline": True}),
                "lighting_mode": (["auto", "manual"], {"default": "auto"}),
                "manual_lighting": ("STRING", {"default": _DEF["manual_lighting"],
                                               "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "shadow_dir")
    FUNCTION = "run"
    CATEGORY = "product-scene"

    def run(self, product_image, product_mask, scene, visual_style, camera,
            reserved_space, lighting_mode, manual_lighting):
        # rebuild RGBA (raises NoAlphaError on a non-cut-out input)
        rgba = TIO.product_to_rgba(product_image, product_mask)

        # always analyze: shadow_dir is needed downstream regardless of lighting mode
        profile = AL.analyze(rgba)
        lighting = (profile.lighting_clause() if lighting_mode == "auto"
                    else manual_lighting.strip())

        scene_cfg = {
            "scene": scene.strip(),
            "visual_style": visual_style.strip(),
            "lighting": lighting,
            "camera": camera.strip(),
            "reserved_space": reserved_space.strip(),
        }
        template = (_ROOT / "prompts" / "scene_prompt_template.txt").read_text(
            encoding="utf-8")
        negative = (_ROOT / "prompts" / "negative_prompt.txt").read_text(
            encoding="utf-8").strip()
        positive = PB.build_positive(scene_cfg, template)

        return (positive, negative, profile.shadow_dir)


NODE_CLASS_MAPPINGS = {"AnalyzeProductLighting": AnalyzeProductLighting}
NODE_DISPLAY_NAME_MAPPINGS = {"AnalyzeProductLighting": "Analyze Product Lighting"}
