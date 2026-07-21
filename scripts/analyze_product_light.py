"""Analyze the lighting of a product photo so the background can be generated
to MATCH the product (product-led lighting).

The product PNG is the fixed anchor (its pixels are never changed). We read its
lighting cues and turn them into (a) a prompt clause for background generation
and (b) a shadow fall direction. Pure PIL statistics over the alpha-masked
product region — rule-based, no model.

Reliability note: colour-temperature / brightness / softness transfer well;
light *direction* from a single photo is a best-effort estimate. All outputs are
overridable upstream (scene.json lighting can be set explicitly).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageStat


@dataclass
class LightProfile:
    temperature: str      # warm | neutral | cool
    key: str              # bright high-key | natural | dim low-key
    softness: str         # soft diffused | moderate | hard directional
    direction: str        # from the left | from the right | from above | even frontal
    shadow_dir: str       # left | right | none   (where the cast shadow falls)

    def lighting_clause(self) -> str:
        """A natural-language lighting description for the background prompt."""
        return (f"{self.softness} {self.temperature} light, {self.direction}, "
                f"{self.key} exposure")

    def as_dict(self) -> dict:
        return {
            "temperature": self.temperature, "key": self.key,
            "softness": self.softness, "direction": self.direction,
            "shadow_dir": self.shadow_dir, "clause": self.lighting_clause(),
        }


def _masked_mean_l(gray: Image.Image, mask: Image.Image) -> float:
    stat = ImageStat.Stat(gray, mask)
    return stat.mean[0]


def analyze(img: Image.Image) -> LightProfile:
    """img: RGBA product (ideally already tight-cropped)."""
    img = img.convert("RGBA")
    alpha = img.getchannel("A")
    rgb = img.convert("RGB")
    gray = img.convert("L")

    # colour temperature: warmth = (R - B) normalised
    r, g, b = ImageStat.Stat(rgb, alpha).mean
    warmth = (r - b) / max(1.0, (r + b))
    if warmth > 0.08:
        temperature = "warm"
    elif warmth < -0.08:
        temperature = "cool"
    else:
        temperature = "neutral"

    # key: overall brightness
    mean_l = _masked_mean_l(gray, alpha) / 255.0
    if mean_l > 0.62:
        key = "bright high-key"
    elif mean_l < 0.38:
        key = "dim low-key"
    else:
        key = "natural balanced"

    # softness: luminance spread inside the product
    std_l = ImageStat.Stat(gray, alpha).stddev[0] / 255.0
    if std_l > 0.22:
        softness = "hard directional"
    elif std_l < 0.12:
        softness = "soft diffused"
    else:
        softness = "moderately soft"

    # direction: compare masked brightness of left/right and top/bottom halves
    w, h = img.size
    def region_mean(box):
        return _masked_mean_l(gray.crop(box), alpha.crop(box))
    left = region_mean((0, 0, w // 2, h))
    right = region_mean((w // 2, 0, w, h))
    top = region_mean((0, 0, w, h // 2))
    bottom = region_mean((0, h // 2, w, h))

    def rel(a, c):
        return (a - c) / max(1.0, (a + c))
    h_diff = rel(left, right)
    v_diff = rel(top, bottom)
    TH = 0.06

    if abs(h_diff) < TH and v_diff > TH:
        direction, shadow_dir = "from above", "none"
    elif h_diff >= TH:
        direction, shadow_dir = "from the left", "right"
    elif h_diff <= -TH:
        direction, shadow_dir = "from the right", "left"
    else:
        direction, shadow_dir = "even and frontal", "right"  # default subtle right

    # upper-side hint refines a strong horizontal read
    if abs(h_diff) >= TH and v_diff > TH:
        side = "left" if h_diff > 0 else "right"
        direction = f"from the upper {side}"

    return LightProfile(temperature, key, softness, direction, shadow_dir)


def analyze_path(path: str | Path) -> LightProfile:
    return analyze(Image.open(path))


if __name__ == "__main__":
    import sys, json
    p = sys.argv[1] if len(sys.argv) > 1 else "inputs/products/product.png"
    print(json.dumps(analyze_path(p).as_dict(), ensure_ascii=False, indent=2))
