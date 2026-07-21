"""Phase 3 — automatic contact-surface detection from a generated background.

Replaces Phase 1's fixed `scene.json.surface_line_frac` with a per-image estimate:
run a monocular depth map (Depth-Anything-V2-Small), then pick the FRONTMOST /
LOWEST large horizontal plane and return its top edge as a frame fraction.

Design constraints (see plans/phase3-depth-detection.md, decisions #3/#4/#5):
  - model = transformers `depth-anything/Depth-Anything-V2-Small-hf`
  - must run in a torch-capable env (ComfyUI's .venv; MPS if available)
  - stacked surfaces: must NOT grab the first (nearer/higher) plane (sofa seat,
    stair tread) — pick the plane a centered product would actually rest on
  - scope = front / mild-tilt surfaces only; a strongly tilted or top-down plane,
    a low-confidence read, or a missing model -> report low confidence so the
    caller (generate.py, Task 3) falls back to the config value

The module is import-light: torch/transformers are imported lazily inside the
backend, so `detect_surface(...)` degrades to a fallback result (never crashes)
when the ML stack or the model download is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

MODEL_ID = "depth-anything/Depth-Anything-V2-Small-hf"

# module-level model cache so batch runs load weights once
_BACKEND = None


@dataclass
class SurfaceResult:
    """Everything geometry / generate.py needs to place the product base.

    `frac` is always usable: it is the detected value when confident, otherwise
    the caller-supplied fallback. `detected_frac` is None when detection failed.
    """
    frac: float                 # final recommended contact line (0..1 of frame height)
    confidence: float           # 0..1
    used_fallback: bool
    width_frac: float           # usable flat width at the surface (0..1 of frame width)
    detected_frac: Optional[float]
    reason: str                 # one-line human/log explanation

    def surface_y(self, frame_h: int) -> int:
        return round(frame_h * self.frac)

    def as_dict(self) -> dict:
        return asdict(self)


class DepthBackend:
    """Lazy wrapper around transformers depth estimation. Loads weights once."""

    def __init__(self, model_id: str = MODEL_ID, device: Optional[str] = None):
        self.model_id = model_id
        self._device = device
        self._proc = None
        self._model = None

    def _ensure(self):
        if self._model is not None:
            return
        import torch  # lazy: keeps the module importable without torch
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation

        if self._device is None:
            self._device = "mps" if torch.backends.mps.is_available() else "cpu"
        self._proc = AutoImageProcessor.from_pretrained(self.model_id)
        self._model = (
            AutoModelForDepthEstimation.from_pretrained(self.model_id)
            .to(self._device)
            .eval()
        )

    def depth(self, img: Image.Image) -> np.ndarray:
        """Return a HxW float depth map, larger = closer to camera."""
        import torch

        self._ensure()
        W, H = img.size
        inputs = self._proc(images=img, return_tensors="pt").to(self._device)
        with torch.no_grad():
            pred = self._model(**inputs).predicted_depth  # (1, h, w)
        depth = torch.nn.functional.interpolate(
            pred.unsqueeze(1), size=(H, W), mode="bicubic", align_corners=False
        ).squeeze().cpu().numpy()
        return depth


def _get_backend(model_id: str, device: Optional[str]) -> DepthBackend:
    global _BACKEND
    if _BACKEND is None or _BACKEND.model_id != model_id:
        _BACKEND = DepthBackend(model_id, device)
    return _BACKEND


def _analyze_depth(depth: np.ndarray) -> dict:
    """Find the dominant horizontal support plane in a depth map.

    A horizontal support surface, seen near eye level, reads as a band of rows
    whose depth increases smoothly downward (the ground receding toward the
    camera). Multiple stacked surfaces => multiple such bands; we take the
    DOMINANT band (largest vertical extent = the plane a product actually rests
    on, not a nearer sliver like a sofa seat or a stair tread) and return its
    TOP edge as the contact line.

    Returns a dict of raw signals; confidence/tilt judgement happens in caller.
    """
    H, W = depth.shape
    d = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)

    # per-row mean depth, then smooth heavily (a support plane is a smooth ramp;
    # mean+strong smoothing avoids fragmenting one ramp into many tiny bands)
    row = d.mean(axis=1)
    k = max(5, H // 40)
    kern = np.ones(k) / k
    rows = np.convolve(row, kern, mode="same")
    vgrad = np.gradient(rows)  # >0 => getting nearer as we go down

    # a row is "receding" if depth is consistently increasing downward. Threshold
    # off a robust scale of the positive gradients so texture noise stays out.
    pos = vgrad[vgrad > 0]
    thr = max(1e-4, np.percentile(pos, 60) * 0.30) if pos.size else 1e9
    receding = vgrad > thr

    # close small gaps so a single ramp with a tiny dip stays one band
    gap = max(2, H // 25)
    run = 0
    for y in range(H):
        if receding[y]:
            run = 0
        else:
            run += 1
            if run <= gap and y - run >= 0 and receding[y - run]:
                # tentatively bridge; only commit if a receding row resumes soon
                look = min(H, y + gap)
                if receding[y:look].any():
                    receding[y] = True
                    run = 0

    # collect contiguous receding bands
    bands = []
    y = 0
    while y < H:
        if receding[y]:
            y0 = y
            while y < H and receding[y]:
                y += 1
            bands.append((y0, y - 1))
        else:
            y += 1

    if not bands:
        return {"ok": False, "bands": [], "H": H, "W": W, "d": d,
                "n_bands": 0, "runner_up_ratio": 0.0,
                "total_depth_span": float(d.max() - d.min())}

    # dominant plane = band with the largest vertical extent
    extents = sorted((b[1] - b[0] + 1 for b in bands), reverse=True)
    # how big is the SECOND plane relative to the dominant one? Two comparably
    # sized horizontal planes (stacked steps / platform+floor / a see-through
    # glass top exposing the floor) => genuinely ambiguous which one a centred
    # product rests on. Caller falls back rather than guessing wrong.
    runner_up_ratio = (extents[1] / extents[0]) if len(extents) >= 2 and extents[0] else 0.0

    y0, y1 = max(bands, key=lambda b: b[1] - b[0])
    span = (y1 - y0 + 1) / H
    top_frac = y0 / H

    # usable flat width at the surface top row: central run within the plane's
    # depth range (tolerance = half a std of that row)
    top_row_d = d[max(0, y0)]
    center = W // 2
    tol = max(0.03, d[y0:y1 + 1].std() * 0.75)
    ref = np.median(top_row_d)
    left = center
    while left > 0 and abs(top_row_d[left] - ref) <= tol:
        left -= 1
    right = center
    while right < W - 1 and abs(top_row_d[right] - ref) <= tol:
        right += 1
    width_frac = (right - left) / W

    return {
        "ok": True, "bands": bands, "H": H, "W": W, "d": d,
        "top_frac": top_frac, "band_span": span,
        "band_top": y0, "band_bottom": y1,
        "n_bands": len(bands), "runner_up_ratio": float(runner_up_ratio),
        "width_frac": float(np.clip(width_frac, 0.0, 1.0)),
        "total_depth_span": float(depth.max() - depth.min()),
    }


def adaptive_front_k(span: float) -> float:
    """Map a plane's vertical span to how far down it the contact line sits.

    A large span means a long surface receding far toward the camera: the far
    edge is deep in the scene, so the product must be pushed further toward the
    NEAR edge to look grounded (bigger k). A shallow band is already near the
    viewer, so a smaller k keeps the base off the very front lip. Linear in span,
    clamped to a sane range. Replaces the Phase 3 global k=0.6 (decision #5)."""
    return float(np.clip(0.50 + 0.60 * float(span), 0.50, 0.80))


def detect_surface(
    image,
    fallback_frac: float = 0.78,
    min_confidence: float = 0.45,
    front_k: Optional[float] = None,
    model_id: str = MODEL_ID,
    device: Optional[str] = None,
) -> SurfaceResult:
    """Estimate the contact-surface line for a generated background.

    `image` may be a path or a PIL image. Always returns a usable `frac`:
    detection when confident, else `fallback_frac`. Never raises on a missing
    model / depth failure — it reports low confidence and falls back instead.
    """
    if isinstance(image, (str, Path)):
        img = Image.open(image).convert("RGB")
    else:
        img = image.convert("RGB")

    def fb(reason: str, conf: float = 0.0, detected=None, width=0.0) -> SurfaceResult:
        return SurfaceResult(
            frac=float(fallback_frac), confidence=conf, used_fallback=True,
            width_frac=width, detected_frac=detected, reason=reason,
        )

    # --- near-solid input (blank / degenerate) -> fallback. The depth model
    #     hallucinates a smooth ramp even on flat colour, so guard on the input
    #     image's own variance rather than trusting the depth output. ---
    img_std = float(np.asarray(img.convert("L"), dtype=np.float32).std())
    if img_std < 6.0:
        return fb(f"near-solid input image (std={img_std:.1f}); fallback", conf=0.05)

    # --- run depth; any failure (no torch / download / runtime) -> fallback ---
    try:
        depth = _get_backend(model_id, device).depth(img)
    except Exception as e:  # noqa: BLE001 - degrade, never crash the pipeline
        return fb(f"depth unavailable ({type(e).__name__}: {e}); using config fallback")

    a = _analyze_depth(depth)

    # degenerate depth (e.g. a solid-colour image) -> no surface signal
    if not a["ok"] or a["total_depth_span"] < 0.5:
        return fb("no clear receding surface (flat/degenerate depth); fallback",
                  conf=0.1)

    top_frac = a["top_frac"]
    span = a["band_span"]

    # --- confidence: bigger, well-placed band = more trustworthy ---
    # span_score: a real support plane occupies a fair chunk but not the whole
    # frame; a huge band starting near the top signals a top-down / tilted plane.
    span_score = float(np.clip(span / 0.30, 0.0, 1.0))
    # scope #4: a plane starting near the top and filling much of the frame has
    # no usable front edge — a top-down / tilted view, or an ambiguous multi-
    # level ramp (stacked steps+platform+floor). Both should fall back.
    tilt = top_frac < 0.22 and span > 0.45
    placement_score = 1.0 if 0.30 <= top_frac <= 0.95 else 0.4
    width_score = float(np.clip(a["width_frac"] / 0.40, 0.0, 1.0))
    confidence = float(np.clip(
        0.45 * span_score + 0.35 * placement_score + 0.20 * width_score, 0.0, 1.0))

    if tilt:
        return fb(
            f"no usable front edge — tilt/top-down or ambiguous ramp "
            f"(span={span:.2f}, top={top_frac:.2f}), out of scope; fallback",
            conf=min(confidence, 0.3),
            detected=round(top_frac, 3), width=a["width_frac"])

    # --- stacked / see-through ambiguity (Phase 5 #2): a runner-up plane nearly
    #     as large as the dominant one means we can't reliably tell which surface
    #     the product should rest on (stacked steps, platform+floor, a glass top
    #     exposing the floor). Fall back rather than pick the wrong plane. ---
    runner_up = a.get("runner_up_ratio", 0.0)
    if runner_up >= 0.70:
        return fb(
            f"ambiguous stacked/see-through planes (runner-up {runner_up:.2f} "
            f"of dominant across {a.get('n_bands', 0)} bands); can't tell which "
            f"to rest on; fallback",
            conf=min(confidence, 0.3),
            detected=round(top_frac, 3), width=a["width_frac"])

    if confidence < min_confidence:
        return fb(
            f"low confidence {confidence:.2f} (span={span:.2f}, "
            f"top={top_frac:.2f}); fallback", conf=confidence,
            detected=round(top_frac, 3), width=a["width_frac"])

    # Contact line = FRONT/near part of the plane, not its far top edge. Placing
    # the product base at the plane's far edge parks it at the back with empty
    # surface in front -> reads as floating (see plans/ Task 4 diagnosis). Move
    # `front_k` of the way down the plane toward the viewer, clamped inside the
    # band and off the very bottom of the frame.
    k = adaptive_front_k(span) if front_k is None else float(front_k)
    near_frac = a["band_bottom"] / a["H"]
    contact = top_frac + k * span
    contact = min(contact, near_frac, 0.92)
    contact = max(contact, top_frac)

    return SurfaceResult(
        frac=round(float(contact), 4), confidence=confidence, used_fallback=False,
        width_frac=a["width_frac"], detected_frac=round(float(contact), 4),
        reason=(f"surface plane [{top_frac:.2f}-{near_frac:.2f}], "
                f"contact @ {contact:.3f} (k={k:.2f}{'auto' if front_k is None else ''}, "
                f"conf={confidence:.2f}, span={span:.2f}, width={a['width_frac']:.2f})"),
    )


# --- CLI: run against fixtures / any background, optional overlay ------------
def _main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="detect contact surface from a background")
    ap.add_argument("images", nargs="+", help="background image path(s)")
    ap.add_argument("--fallback", type=float, default=0.78)
    ap.add_argument("--min-conf", type=float, default=0.45)
    ap.add_argument("--front-k", type=float, default=None,
                    help="how far down the plane the contact line sits (0=far edge); "
                         "default None = adaptive from band span")
    ap.add_argument("--overlay-dir", default=None,
                    help="if set, save an <name>_overlay.png with the detected line")
    args = ap.parse_args(argv)

    from PIL import ImageDraw

    for p in args.images:
        r = detect_surface(p, fallback_frac=args.fallback, min_confidence=args.min_conf,
                           front_k=args.front_k)
        tag = "FALLBACK" if r.used_fallback else "DETECT  "
        print(f"[{tag}] {Path(p).name:32s} frac={r.frac:.3f} "
              f"conf={r.confidence:.2f} w={r.width_frac:.2f} :: {r.reason}")
        if args.overlay_dir:
            img = Image.open(p).convert("RGB")
            y = r.surface_y(img.height)
            draw = ImageDraw.Draw(img)
            colour = (255, 140, 0) if r.used_fallback else (255, 0, 0)
            draw.line([(0, y), (img.width, y)], fill=colour, width=4)
            out = Path(args.overlay_dir) / f"{Path(p).stem}_overlay.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            img.save(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
