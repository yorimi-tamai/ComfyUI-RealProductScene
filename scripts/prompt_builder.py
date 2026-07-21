"""Build the background prompt from scene.json + the prompt template.

Fills the {scene}/{visual_style}/{lighting}/{camera}/{reserved_space}
placeholders in prompts/scene_prompt_template.txt with values from
config/scene.json. Also loads the static negative prompt.
"""

from __future__ import annotations

import json
from pathlib import Path

# placeholders the template understands (also the required scene.json keys)
TEMPLATE_KEYS = ("scene", "visual_style", "lighting", "camera", "reserved_space")


def build_positive(scene_cfg: dict, template_text: str) -> str:
    """Substitute known {key} placeholders. Explicit per-key replace (not
    str.format) so stray braces in the template never crash the build."""
    missing = [k for k in TEMPLATE_KEYS if k not in scene_cfg]
    if missing:
        raise ValueError(f"scene.json missing keys required by template: {missing}")
    text = template_text
    for key in TEMPLATE_KEYS:
        text = text.replace("{" + key + "}", str(scene_cfg[key]))
    return text.strip()


def load_prompts(project_root: str | Path = ".",
                 scene_cfg: dict | None = None) -> tuple[str, str]:
    """Return (positive_prompt, negative_prompt) built from project files.

    Pass `scene_cfg` to override what's on disk (e.g. after substituting an
    auto-derived lighting clause); otherwise config/scene.json is read."""
    root = Path(project_root)
    if scene_cfg is None:
        scene_cfg = json.loads(
            (root / "config" / "scene.json").read_text(encoding="utf-8"))
    template = (root / "prompts" / "scene_prompt_template.txt").read_text(encoding="utf-8")
    negative = (root / "prompts" / "negative_prompt.txt").read_text(encoding="utf-8").strip()
    positive = build_positive(scene_cfg, template)
    return positive, negative


if __name__ == "__main__":
    pos, neg = load_prompts(Path(__file__).resolve().parent.parent)
    print("=== POSITIVE ===\n" + pos)
    print("\n=== NEGATIVE ===\n" + neg)
