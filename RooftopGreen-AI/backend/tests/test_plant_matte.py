"""backend/tests/test_plant_matte.py - synthetic regression test for the plant-matte compositor."""
import io
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
try:
    from app.services.plant_matte import composite_plant_matte
except ImportError:                                  # allow running standalone
    from composite_ref import composite_plant_matte

W, H = 1152, 864
PINS = [{"x": .18, "y": .47}, {"x": .82, "y": .47}, {"x": .97, "y": .93}, {"x": .03, "y": .93}]
PLANTS = {  # name: (cx, base_y, rx, ry)  canopy centre is base_y - ry
    "tall_midground": (int(.50 * W), int(.50 * H), 60, 130),   # canopy rises ABOVE the floor's far edge
    "left_mid": (int(.30 * W), int(.62 * H), 70, 70),
    "right_mid": (int(.70 * W), int(.66 * H), 80, 85),
    "foreground": (int(.50 * W), int(.97 * H), 120, 90),        # touches the image bottom
}


def _enc(im):
    b = io.BytesIO(); im.save(b, "JPEG", quality=92); return b.getvalue()


def _scene():
    rng = np.random.default_rng(7)
    px = np.zeros((H, W, 3), np.float32)
    for y in range(int(.34 * H)):
        t = y / (.34 * H); px[y, :] = (120 + 60 * t, 170 + 40 * t, 230)
    px[int(.30 * H):int(.36 * H)] = (150, 150, 160)
    px[int(.36 * H):int(.45 * H)] = (170, 160, 150)
    px[int(.45 * H):] = (140, 140, 138)
    px += rng.normal(0, 3, px.shape)
    orig = Image.fromarray(np.clip(px, 0, 255).astype(np.uint8))
    ImageDraw.Draw(orig).line([(0, int(.45 * H)), (W, int(.45 * H))], fill=(90, 85, 80), width=3)
    ai = Image.new("RGB", (W, H)); ai.paste(orig, (2, 1))                    # 2px geometry drift
    ai = ai.point(lambda v: min(255, int(v * 1.04)))                          # +4% brightness
    d = ImageDraw.Draw(ai)
    for cx, by, rx, ry in PLANTS.values():
        d.ellipse([cx - rx, by - 2 * ry, cx + rx, by], fill=(40, 120, 45))
        d.rectangle([cx - rx // 2, by - 12, cx + rx // 2, by + 6], fill=(170, 80, 50))
    fx, fy = int(.15 * W), int(.36 * H)                                       # pot standing ON the parapet
    d.ellipse([fx - 40, fy - 60, fx + 40, fy], fill=(40, 120, 45))
    d.rectangle([fx - 25, fy - 4, fx + 25, fy + 8], fill=(170, 80, 50))
    ai = ai.filter(ImageFilter.GaussianBlur(.6))
    ai = Image.fromarray(np.clip(np.asarray(ai, np.float32) + rng.normal(0, 3, (H, W, 3)), 0, 255).astype(np.uint8))
    return _enc(orig), _enc(ai)


def _greenness(img, mask):
    g = img[..., 1] - .5 * (img[..., 0] + img[..., 2])
    return float((g[mask] > 25).mean())


def test_plants_whole_parapet_pot_removed_no_seam():
    ob, ab = _scene()
    out, meta = composite_plant_matte(ob, ab, PINS)
    res = np.asarray(Image.open(io.BytesIO(out)).convert("RGB"), np.float32)
    orig = np.asarray(Image.open(io.BytesIO(ob)).convert("RGB"), np.float32)
    assert meta["composite_mode"] == "plant_matte"
    for name, (cx, by, rx, ry) in PLANTS.items():                              # no plant is sliced
        m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).ellipse([cx - rx, by - 2 * ry, cx + rx, by], fill=255)
        assert _greenness(res, np.asarray(m) > 0) > .90, name
    fx, fy = int(.15 * W), int(.36 * H)                                        # floating pot rejected
    pm = np.zeros((H, W), bool); pm[fy - 62:fy + 8, fx - 45:fx + 45] = True
    assert _greenness(res, pm) < .02
    row = np.abs(res - orig).mean(axis=(1, 2))                                 # no horizontal seam
    assert np.abs(np.diff(row)).max() < 12
    assert meta["width"] == W and meta["height"] == H


def test_no_pins_still_works_and_never_crashes():
    ob, ab = _scene()
    out, meta = composite_plant_matte(ob, ab, [])
    assert Image.open(io.BytesIO(out)).size == (W, H)


def test_pixel_coordinates_are_rejected_not_guessed():
    ob, ab = _scene()
    _, meta = composite_plant_matte(ob, ab, [{"x": 500, "y": 400}] * 4)
    assert meta["pins_used"] == 0
