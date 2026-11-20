"""
Reference implementation: silhouette-following "plant matte" compositing.

Why: the old composite_garden_onto_floor() used a full-width horizontal rectangle mask
(blurred), so any plant crossing that y-line was sliced and any AI geometry drift showed
as a seam. Here the mask follows the *objects the AI added* (found by differencing the
AI render against the original), keeps only objects whose base sits on the user's floor
polygon, and is feathered a few pixels. No geometric boundary ever crosses a plant.
"""
import io
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from scipy import ndimage as ndi

ANALYSIS_LONG_SIDE = 768          # matte is computed at this size, applied at full size
DIFF_THRESHOLD = float(os.getenv("MATTE_DIFF_THRESHOLD", "30"))   # RGB L2 distance (0-255)
MIN_COMPONENT_FRAC = 0.0004       # drop blobs < 0.04% of the frame
BASE_BAND_FRAC = 0.20             # bottom 20% of a blob = its "footprint"
BASE_ON_FLOOR_MIN = 0.50          # >=50% of footprint pixels must lie on the floor zone
OVERLAP_ON_FLOOR_MIN = 0.60       # ...or >=60% of the whole blob lies on the floor zone
FLOOR_MARGIN_FRAC = 0.012         # pin-imprecision tolerance, fraction of long side
NO_PIN_FLOOR_TOP = 0.40           # no pins -> floor is everything below 40% of height
MIN_COVERAGE_FOR_MATTE = 0.003    # below this the AI added nothing -> use full AI frame
GAIN_CLIP = (0.80, 1.25)


def _load_rgb(b: bytes) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(io.BytesIO(b))).convert("RGB")


def _convex_hull(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def parse_pins(pins: Optional[List[Any]]) -> List[Tuple[float, float]]:
    """Accept ONLY normalized {x,y} / [x,y] in [0,1]. Anything else is dropped (never guessed)."""
    out = []
    for p in pins or []:
        try:
            if isinstance(p, dict):
                x, y = float(p["x"]), float(p["y"])
            else:
                x, y = float(p[0]), float(p[1])
        except Exception:
            continue
        if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
            out.append((x, y))
    return out


def _floor_zone(pins: List[Tuple[float, float]], w: int, h: int) -> np.ndarray:
    margin = max(2, int(round(FLOOR_MARGIN_FRAC * max(w, h))))
    if len(pins) >= 3:
        hull = _convex_hull([(x * (w - 1), y * (h - 1)) for x, y in pins])
        img = Image.new("L", (w, h), 0)
        ImageDraw.Draw(img).polygon(hull, fill=255)
        m = np.asarray(img) > 0
    else:
        m = np.zeros((h, w), bool)
        m[int(NO_PIN_FLOOR_TOP * h):, :] = True
    m = ndi.binary_dilation(m, iterations=margin)
    # anything below the far edge of the floor, in the same columns, is nearer floor
    any_col = m.any(axis=0)
    top = np.where(any_col, m.argmax(axis=0), h)
    return np.arange(h)[:, None] >= top[None, :]


def _plant_matte(o: np.ndarray, a: np.ndarray, floor: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    h, w = o.shape[:2]
    os_ = np.stack([ndi.gaussian_filter(o[..., c], 1.5) for c in range(3)], -1)
    as_ = np.stack([ndi.gaussian_filter(a[..., c], 1.5) for c in range(3)], -1)
    d = np.sqrt(((as_ - os_) ** 2).mean(axis=2))
    m = d > DIFF_THRESHOLD
    m = ndi.binary_opening(m, structure=np.ones((5, 5), bool))     # kills 1-4px edge-drift lines
    m = ndi.binary_closing(m, structure=np.ones((9, 9), bool))     # fills foliage gaps
    m = ndi.binary_fill_holes(m)

    lab, n = ndi.label(m)
    keep = np.zeros(n + 1, bool)
    min_area = max(1, int(MIN_COMPONENT_FRAC * w * h))
    kept = rejected = 0
    for i, sl in enumerate(ndi.find_objects(lab), start=1):
        comp = lab[sl] == i
        area = int(comp.sum())
        if area < min_area:
            rejected += 1
            continue
        fl = floor[sl]
        overlap = (comp & fl).sum() / area
        rows = np.nonzero(comp.any(axis=1))[0]
        y0, y1 = rows[0], rows[-1]
        band_h = max(1, int(round(BASE_BAND_FRAC * (y1 - y0 + 1))))
        band = comp[y1 - band_h + 1:y1 + 1]
        base_ratio = (band & fl[y1 - band_h + 1:y1 + 1]).sum() / max(1, band.sum())
        if base_ratio >= BASE_ON_FLOOR_MIN or overlap >= OVERLAP_ON_FLOOR_MIN:
            keep[i] = True
            kept += 1
        else:
            rejected += 1
    matte = keep[lab]
    matte = ndi.binary_dilation(matte, iterations=2)                # let feather land on AI pixels
    return matte, {"components_kept": kept, "components_rejected": rejected}


def composite_plant_matte(
    original_bytes: bytes,
    ai_bytes: bytes,
    pins_norm: Optional[List[Any]] = None,
    mode: str = "plant_matte",
    debug_dir: Optional[str] = None,
) -> Tuple[bytes, Dict[str, Any]]:
    orig = _load_rgb(original_bytes)
    W, H = orig.size
    ai = _load_rgb(ai_bytes)
    aw, ah = ai.size
    meta: Dict[str, Any] = {"width": W, "height": H, "ai_size": [aw, ah]}

    # 1) Align: never stretch. If aspect differs >1%, centre-crop the AI frame to the original aspect.
    aspect_err = (aw / ah) / (W / H) - 1.0
    meta["aspect_error"] = round(aspect_err, 4)
    if abs(aspect_err) > 0.01:
        if aw / ah > W / H:
            nw = round(ah * W / H); x0 = (aw - nw) // 2; ai = ai.crop((x0, 0, x0 + nw, ah))
        else:
            nh = round(aw * H / W); y0 = (ah - nh) // 2; ai = ai.crop((0, y0, aw, y0 + nh))
    if ai.size != (W, H):
        ai = ai.resize((W, H), Image.Resampling.LANCZOS)

    # 2) Analysis scale
    s = min(1.0, ANALYSIS_LONG_SIDE / max(W, H))
    w, h = max(1, round(W * s)), max(1, round(H * s))
    o_s = np.asarray(orig.resize((w, h), Image.Resampling.LANCZOS), dtype=np.float32)
    a_s = np.asarray(ai.resize((w, h), Image.Resampling.LANCZOS), dtype=np.float32)

    # 3) Global tone alignment: per-channel median ratio (plants are a minority of pixels)
    gain = np.clip(np.median(((a_s + 1.0) / (o_s + 1.0)).reshape(-1, 3), axis=0), *GAIN_CLIP)
    meta["gain"] = [round(float(g), 3) for g in gain]
    a_s = np.clip(a_s / gain, 0, 255)
    ai_full = np.clip(np.asarray(ai, dtype=np.float32) / gain, 0, 255)

    if mode == "ai_full_frame":
        out = Image.fromarray(ai_full.astype(np.uint8))
        meta["composite_mode"] = "ai_full_frame"
        return _encode(out), meta

    pins = parse_pins(pins_norm)
    meta["pins_used"] = len(pins)
    floor = _floor_zone(pins, w, h)
    matte, mm = _plant_matte(o_s, a_s, floor)
    meta.update(mm)
    coverage = float(matte.mean())
    meta["matte_coverage"] = round(coverage, 4)

    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        Image.fromarray((matte * 255).astype(np.uint8)).save(os.path.join(debug_dir, "matte.png"))
        Image.fromarray((floor * 255).astype(np.uint8)).save(os.path.join(debug_dir, "floor.png"))

    if coverage < MIN_COVERAGE_FOR_MATTE:
        meta["composite_mode"] = "ai_full_frame"      # AI added nothing recognisable on the floor
        return _encode(Image.fromarray(ai_full.astype(np.uint8))), meta

    # 4) Feathered alpha at full resolution
    feather = max(2.0, 0.004 * max(W, H))
    alpha_img = Image.fromarray((matte * 255).astype(np.uint8)).resize((W, H), Image.Resampling.BICUBIC)
    alpha = np.asarray(alpha_img.filter(ImageFilter.GaussianBlur(radius=feather)), dtype=np.float32)[..., None] / 255.0

    # 5) Mild sharpen on the AI layer only (it was upscaled); original pixels are never touched
    ai_sharp = Image.fromarray(ai_full.astype(np.uint8)).filter(ImageFilter.UnsharpMask(radius=1.2, percent=70, threshold=2))
    out = np.asarray(orig, dtype=np.float32) * (1.0 - alpha) + np.asarray(ai_sharp, dtype=np.float32) * alpha
    meta["composite_mode"] = "plant_matte"
    return _encode(Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))), meta


def _encode(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92, subsampling=0, optimize=True)
    return buf.getvalue()
