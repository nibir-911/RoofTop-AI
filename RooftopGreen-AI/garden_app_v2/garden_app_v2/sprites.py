"""Approved plant sprite library. Only sprites whose manifest status is 'approved' are ever used.
Layout: data/sprites/<plant_id>/manifest.json + <stage>.png (RGBA cut-out, plant standing in its pot).
Stages: planting (day 1), mid (~3 months), mature."""
import datetime, json, os
import cv2

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sprites")
STAGES = ("planting", "mid", "mature")
_cache = {}


def _mpath(pid, base=None):
    return os.path.join(base or DIR, pid, "manifest.json")


def read_manifest(pid, base=None):
    p = _mpath(pid, base)
    if not os.path.exists(p):
        return {"plant_id": pid, "stages": {}}
    return json.load(open(p, encoding="utf-8"))


def approve(pid, stage, png_path, reviewer, model="", prompt="", seed=None, base=None):
    """Copy a reviewed PNG into the library and mark it approved (used by tools/review_sprites.py)."""
    import shutil
    assert stage in STAGES
    d = os.path.join(base or DIR, pid)
    os.makedirs(d, exist_ok=True)
    shutil.copyfile(png_path, os.path.join(d, f"{stage}.png"))
    m = read_manifest(pid, base)
    m["stages"][stage] = {"file": f"{stage}.png", "status": "approved", "reviewer": reviewer,
                          "date": datetime.date.today().isoformat(), "model": model, "prompt": prompt, "seed": seed}
    json.dump(m, open(_mpath(pid, base), "w", encoding="utf-8"), indent=2)
    _cache.clear()


def reject(pid, stage, base=None):
    m = read_manifest(pid, base)
    if stage in m["stages"]:
        m["stages"][stage]["status"] = "rejected"
        os.makedirs(os.path.join(base or DIR, pid), exist_ok=True)
        json.dump(m, open(_mpath(pid, base), "w", encoding="utf-8"), indent=2)
    _cache.clear()


def load_sprite(pid, stage, base=None):
    """BGRA image if (and only if) this plant+stage sprite is approved; otherwise None."""
    key = (base or DIR, pid, stage)
    if key in _cache:
        return _cache[key]
    img = None
    e = read_manifest(pid, base).get("stages", {}).get(stage)
    if e and e.get("status") == "approved":
        path = os.path.join(base or DIR, pid, e["file"])
        if os.path.exists(path):
            im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if im is not None and im.ndim == 3 and im.shape[2] == 4:
                img = im
    _cache[key] = img
    return img


def coverage(plant_ids, base=None):
    """{plant_id: [approved stages]} for reporting."""
    return {pid: [s for s in STAGES if load_sprite(pid, s, base) is not None] for pid in plant_ids}


def paste_rgba(canvas, spr, cx, bottom_y, target_h):
    """Alpha-paste sprite so its bottom-centre sits at (cx, bottom_y) with the given pixel height."""
    h, w = spr.shape[:2]
    s = max(target_h, 4) / h
    nw, nh = max(2, int(w * s)), max(2, int(h * s))
    r = cv2.resize(spr, (nw, nh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
    x0, y0 = int(cx - nw / 2), int(bottom_y - nh)
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(canvas.shape[1], x0 + nw), min(canvas.shape[0], y0 + nh)
    if X1 <= X0 or Y1 <= Y0:
        return
    sub = r[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    a = sub[..., 3:4] / 255.0
    canvas[Y0:Y1, X0:X1] = (sub[..., :3] * a + canvas[Y0:Y1, X0:X1] * (1 - a)).astype("uint8")
