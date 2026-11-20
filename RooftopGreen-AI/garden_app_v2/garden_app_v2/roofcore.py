"""Core logic for the rooftop railing / grid tool (no Streamlit, no files)."""
import csv, io, math
from collections import namedtuple
import cv2
import numpy as np
from PIL import Image, ImageOps

CellType = namedtuple("CellType", "code label bgr letter emoji")
TYPES = [
    CellType("FULL_SUN",      "Full Sun (all day)",            (0, 215, 255),   "F", "🟨"),
    CellType("MORNING_SUN",   "Morning Sun (first half)",      (0, 140, 255),   "M", "🟧"),
    CellType("AFTERNOON_SUN", "Afternoon Sun (second half)",   (255, 140, 0),   "A", "🟦"),
    CellType("SHADE",         "Shade (little or no sun)",      (160, 70, 130),  "S", "🟪"),
    CellType("BLOCKED",       "Blocked (tank, stairs, pipes)", (50, 50, 220),   "X", "🟥"),
    CellType("WALKWAY",       "Walkway (keep clear)",          (170, 170, 170), "W", "⬜"),
]
BY_CODE = {t.code: t for t in TYPES}


# ------------------------------------------------------------------ images
def decode_image(data: bytes, max_side=2400):
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)).convert("RGB"))
    bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    s = max_side / max(bgr.shape[:2])
    if s < 1:
        bgr = cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return bgr


def to_pil(bgr):
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def encode_png(bgr):
    ok, buf = cv2.imencode(".png", bgr)
    return buf.tobytes()


# ------------------------------------------------------------------ geometry
def _circle_intersections(p0, r0, p1, r1):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    d = math.hypot(dx, dy)
    if d > r0 + r1 or d < abs(r0 - r1) or d == 0:
        raise ValueError("These lengths cannot form a closed 4-sided shape. Re-check the measurements.")
    k = (r0 ** 2 - r1 ** 2 + d ** 2) / (2 * d)
    h = math.sqrt(max(r0 ** 2 - k ** 2, 0))
    mx, my = p0[0] + k * dx / d, p0[1] + k * dy / d
    return [(mx + h * dy / d, my - h * dx / d), (mx - h * dy / d, my + h * dx / d)]


def _cross(u, v):
    return u[0] * v[1] - u[1] * v[0]


def compute_corners(lengths, diagonal=None):
    """lengths = [AB, BC, CD, DA]; diagonal = AC (optional). Returns corners, area, note."""
    a, b, c, e = lengths
    A = (0.0, 0.0)
    if diagonal:
        B = (a, 0.0)
        C = max(_circle_intersections(B, b, A, diagonal), key=lambda p: p[1])
        ac = (C[0] - A[0], C[1] - A[1])
        side_b = _cross(ac, (B[0] - A[0], B[1] - A[1]))
        D = [p for p in _circle_intersections(A, e, C, c)
             if _cross(ac, (p[0] - A[0], p[1] - A[1])) * side_b < 0][0]
        note = f"Built from side lengths + diagonal AC = {diagonal} ft."
    else:
        w, h = (a + c) / 2, (b + e) / 2
        B, C, D = (w, 0.0), (w, h), (0.0, h)
        note = f"No diagonal given: assuming a rectangle {w:.1f} x {h:.1f} ft."
    corners = [A, B, C, D]
    area = 0.5 * abs(sum(corners[i][0] * corners[(i + 1) % 4][1] -
                         corners[(i + 1) % 4][0] * corners[i][1] for i in range(4)))
    return corners, area, note


def outline_image(corners, size=380, bearing=None):
    pts = np.array(corners, float)
    mn, mx = pts.min(0), pts.max(0)
    sc = (size - 80) / max((mx - mn).max(), 1e-6)
    img = np.full((size, size, 3), 255, np.uint8)
    px = [(int(40 + (p[0] - mn[0]) * sc), int(size - 40 - (p[1] - mn[1]) * sc)) for p in pts]
    cv2.fillPoly(img, [np.array(px)], (225, 225, 220))
    cv2.polylines(img, [np.array(px)], True, (40, 40, 40), 2)
    for name, q in zip("ABCD", px):
        cv2.putText(img, name, (q[0] + 6, q[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 160), 2, cv2.LINE_AA)
    for i in range(4):
        p, q = pts[i], pts[(i + 1) % 4]
        m = ((px[i][0] + px[(i + 1) % 4][0]) // 2, (px[i][1] + px[(i + 1) % 4][1]) // 2)
        cv2.putText(img, f"{math.dist(p, q):.1f}ft", (m[0] - 20, m[1] + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (20, 20, 20), 1, cv2.LINE_AA)
    if bearing is not None:
        draw_compass(img, bearing, center=(size - 48, 48), r=24)
    return img


# ------------------------------------------------------------------ compass
def north_angle_deg(bearing):
    """Side 1 is the bottom edge of the plan and faces compass `bearing` (0=N, 90=E, 180=S).
    Returns degrees clockwise from 'up' in the image at which NORTH points."""
    return (180.0 - bearing) % 360.0


def compass_name(bearing):
    names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return names[int(((bearing % 360) + 22.5) // 45) % 8]


def north_vector(bearing):
    """Unit vector (dx, dy) of north in image coordinates (x right, y down)."""
    a = math.radians(north_angle_deg(bearing))
    return (math.sin(a), -math.cos(a))


def draw_compass(img, bearing, center=None, r=34):
    h, w = img.shape[:2]
    cx, cy = center if center else (w - r - 34, r + 34)
    cv2.circle(img, (cx, cy), r + 22, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), r + 22, (60, 60, 60), 1, cv2.LINE_AA)
    phi = math.radians(north_angle_deg(bearing))
    for label, off in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
        a = phi + math.radians(off)
        dx, dy = math.sin(a), -math.cos(a)
        tip = (int(cx + dx * r), int(cy + dy * r))
        if label == "N":
            cv2.arrowedLine(img, (cx, cy), tip, (0, 0, 220), 3, cv2.LINE_AA, tipLength=0.35)
        else:
            cv2.line(img, (cx, cy), (int(cx + dx * r * 0.6), int(cy + dy * r * 0.6)), (110, 110, 110), 1, cv2.LINE_AA)
        lp = (int(cx + dx * (r + 12)) - 6, int(cy + dy * (r + 12)) + 6)
        cv2.putText(img, label, lp, cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 0, 200) if label == "N" else (60, 60, 60), 2 if label == "N" else 1, cv2.LINE_AA)
    return img


# ------------------------------------------------------------------ railing strips
def make_strip(img, quad, length_ft, ppf, height_ft, mirror=False):
    W, H = int(length_ft * ppf), int(height_ft * ppf)
    src = np.float32(quad)
    dst = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    M = cv2.getPerspectiveTransform(src, dst)
    strip = cv2.warpPerspective(img, M, (W, H), flags=cv2.INTER_AREA)
    return cv2.flip(strip, 1) if mirror else strip


def render_foldout(corners, strips, lengths, ppf, height_ft, floor_bgr=(190, 190, 185)):
    corners = np.array(corners, float)
    panel_h = height_ft * ppf
    margin = int(panel_h + 80)
    minx, miny = corners.min(0)
    maxx, maxy = corners.max(0)
    Wc = int((maxx - minx) * ppf + 2 * margin)
    Hc = int((maxy - miny) * ppf + 2 * margin)
    to_px = lambda p: np.array([margin + (p[0] - minx) * ppf, margin + (maxy - p[1]) * ppf], float)
    pts = np.array([to_px(p) for p in corners])
    centroid = pts.mean(0)
    canvas = np.full((Hc, Wc, 3), 245, np.uint8)
    fm = np.zeros((Hc, Wc), np.uint8)
    cv2.fillPoly(fm, [pts.astype(np.int32)], 255)
    canvas[fm > 0] = floor_bgr
    for i in range(4):
        P, Q = pts[i], pts[(i + 1) % 4]
        t = Q - P
        n = np.array([t[1], -t[0]])
        n /= np.linalg.norm(n)
        if np.dot(n, (P + Q) / 2 - centroid) < 0:
            n = -n
        dst = np.float32([P + n * panel_h, Q + n * panel_h, Q, P])
        h, w = strips[i].shape[:2]
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        warped = cv2.warpPerspective(strips[i], cv2.getPerspectiveTransform(src, dst), (Wc, Hc))
        m = np.zeros((Hc, Wc), np.uint8)
        cv2.fillConvexPoly(m, dst.astype(np.int32), 255)
        canvas[m > 0] = warped[m > 0]
        cv2.polylines(canvas, [dst.astype(np.int32)], True, (60, 60, 60), 1)
    cv2.polylines(canvas, [pts.astype(np.int32)], True, (30, 30, 30), 2)
    font = cv2.FONT_HERSHEY_SIMPLEX
    for i, name in enumerate("ABCD"):
        inward = centroid - pts[i]
        inward /= np.linalg.norm(inward)
        pos = pts[i] + inward * 22
        cv2.putText(canvas, name, (int(pos[0]) - 8, int(pos[1]) + 8), font, 0.8, (0, 0, 160), 2, cv2.LINE_AA)
    return canvas


# ------------------------------------------------------------------ realistic render
def _noise(rng, shape, scale):
    h, wd = shape
    small = rng.random((max(2, h // scale), max(2, wd // scale))).astype(np.float32)
    return cv2.resize(small, (wd, h), interpolation=cv2.INTER_CUBIC)


def _mirror_tile(t, h, wd):
    row = np.hstack([t, t[:, ::-1]])
    blk = np.vstack([row, row[::-1]])
    ry, rx = int(np.ceil(h / blk.shape[0])), int(np.ceil(wd / blk.shape[1]))
    return np.tile(blk, (ry, rx, 1))[:h, :wd]


def render_realistic(strips, lengths, ppf, floor_sample=None, seed=7, joint_ft=10,
                     tex_scale_ft=4.0, base_bgr=(112, 118, 120), detail_gain=1.0):
    """Rectangular roof. side1=bottom, side2=right, side3=top, side4=left. Returns (image, info)."""
    rng = np.random.default_rng(seed)
    W = int(round((lengths[0] + lengths[2]) / 2 * ppf))
    Hf = int(round((lengths[1] + lengths[3]) / 2 * ppf))
    PH = strips[0].shape[0]

    def canon(strip, length, flip_u):
        s = cv2.resize(strip, (length, PH), interpolation=cv2.INTER_AREA)[::-1]
        return s[:, ::-1] if flip_u else s

    cb, cr = canon(strips[0], W, False), canon(strips[1], Hf, True)
    ct, cl = canon(strips[2], W, True), canon(strips[3], Hf, False)
    OW, OH = W + 2 * PH, Hf + 2 * PH
    X, Y = np.meshgrid(np.arange(OW, dtype=np.float32), np.arange(OH, dtype=np.float32))
    fx, fy = X - PH, Y - PH
    d_left, d_right, d_top, d_bot = -fx, fx - (W - 1), -fy, fy - (Hf - 1)
    dists = np.stack([d_bot, d_right, d_top, d_left])

    def layer(cn, length, v, u_img):
        v = np.clip(v, 0, PH - 1)
        u = np.clip((u_img + v) / (length - 1 + 2 * v) * (length - 1), 0, length - 1)
        return cv2.remap(cn, u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REPLICATE)

    layers = [layer(cb, W, d_bot, fx), layer(cr, Hf, d_right, fy),
              layer(ct, W, d_top, fx), layer(cl, Hf, d_left, fy)]
    soft = max(6, PH * 0.12)
    w = []
    for k in range(4):
        other = np.max(np.delete(dists, k, axis=0), axis=0)
        w.append(np.clip((dists[k] - other) / soft + 0.5, 0, 1))
    w = np.stack(w)
    w /= np.maximum(w.sum(axis=0), 1e-6)
    walls = sum(layers[k].astype(np.float32) * w[k][..., None] for k in range(4))

    fh, fw = Hf, W
    if floor_sample is not None:
        p = floor_sample.astype(np.float32)
        tw = max(24, int(tex_scale_ft * ppf))
        p = cv2.resize(p, (tw, max(24, int(p.shape[0] * tw / p.shape[1]))), interpolation=cv2.INTER_AREA)
        mean = p.reshape(-1, 3).mean(0)
        hp = p - cv2.GaussianBlur(p, (0, 0), max(3, min(p.shape[:2]) / 5))
        t1 = _mirror_tile(hp, fh, fw)
        hp2 = cv2.resize(np.ascontiguousarray(hp.transpose(1, 0, 2)), None, fx=1.7, fy=1.7)
        t2 = _mirror_tile(hp2, fh, fw)
        detail = (t1 + t2) / 1.41 * detail_gain
        low = (_noise(rng, (fh, fw), 140) - 0.5) * 0.16 + 1.0
        stains = np.clip(_noise(rng, (fh, fw), 110) - 0.68, 0, 1) * 1.4
        floor = mean[None, None, :] * low[..., None] * (1 - 0.18 * stains[..., None]) + detail
    else:
        base = np.array(base_bgr, np.float32)
        tex = (0.18 * _noise(rng, (fh, fw), 160) + 0.22 * _noise(rng, (fh, fw), 50) +
               0.30 * _noise(rng, (fh, fw), 10) + 0.30 * _noise(rng, (fh, fw), 3))
        tex = (tex - tex.mean()) / tex.std()
        floor = base[None, None, :] * (1 + 0.10 * tex[..., None])
        stains = np.clip(_noise(rng, (fh, fw), 110) - 0.66, 0, 1) * 1.6
        floor *= (1 - 0.25 * stains[..., None])
        floor += rng.normal(0, 4.0, (fh, fw, 1)).astype(np.float32)

    if joint_ft:
        for gx in range(int(joint_ft * ppf), fw, int(joint_ft * ppf)):
            floor[:, max(gx - 1, 0):gx + 1] *= 0.82
        for gy in range(int(joint_ft * ppf), fh, int(joint_ft * ppf)):
            floor[max(gy - 1, 0):gy + 1, :] *= 0.82
    yy, xx = np.mgrid[0:fh, 0:fw].astype(np.float32)
    edge = np.minimum(np.minimum(xx, fw - 1 - xx), np.minimum(yy, fh - 1 - yy))
    ao = 1 - 0.34 * np.exp(-edge / (0.9 * ppf))
    light = 1.04 - 0.08 * (xx / fw) - 0.05 * (yy / fh)
    floor = np.clip(floor * (ao * light)[..., None], 0, 255)

    out = walls.copy()
    out[PH:PH + fh, PH:PH + fw] = floor
    inside = (d_left < 0) & (d_right < 0) & (d_top < 0) & (d_bot < 0)
    wall_ao = 1 - 0.30 * np.exp(-np.clip(np.max(dists, axis=0), 0, None) / (0.25 * PH))
    out = np.where(inside[..., None], out, out * wall_ao[..., None])
    cx, cy = OW / 2, OH / 2
    vig = 1 - 0.18 * (((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2) / 2
    out = np.clip(out * vig[..., None], 0, 255).astype(np.uint8)
    out = cv2.GaussianBlur(out, (0, 0), 0.6)
    info = {"floor_x0": PH, "floor_y0": PH, "floor_w": W, "floor_h": Hf, "ppf": ppf,
            "image_w": OW, "image_h": OH}
    return out, info


# ------------------------------------------------------------------ grid
def grid_dims(info, grid_ft):
    cell = grid_ft * info["ppf"]
    return math.ceil(info["floor_w"] / cell), math.ceil(info["floor_h"] / cell), cell


def cell_rect(info, grid_ft, r, c):
    cell = grid_ft * info["ppf"]
    x0, y0 = info["floor_x0"] + int(c * cell), info["floor_y0"] + int(r * cell)
    x1 = min(info["floor_x0"] + int((c + 1) * cell), info["floor_x0"] + info["floor_w"])
    y1 = min(info["floor_y0"] + int((r + 1) * cell), info["floor_y0"] + info["floor_h"])
    return x0, y0, x1, y1


def cell_from_xy(info, grid_ft, x, y):
    cols, rows, cell = grid_dims(info, grid_ft)
    c = int((x - info["floor_x0"]) // cell)
    r = int((y - info["floor_y0"]) // cell)
    return (r, c) if (0 <= r < rows and 0 <= c < cols and
                      x < info["floor_x0"] + info["floor_w"] and y < info["floor_y0"] + info["floor_h"]) else None


def render_grid(base, info, grid_ft, cells, highlight=(), letters=True, tap=None, bearing=None):
    cols, rows, cell = grid_dims(info, grid_ft)
    ov = base.copy()
    for k, code in cells.items():
        r, c = map(int, k.split(","))
        x0, y0, x1, y1 = cell_rect(info, grid_ft, r, c)
        cv2.rectangle(ov, (x0, y0), (x1, y1), BY_CODE[code].bgr, -1)
    out = cv2.addWeighted(ov, 0.45, base, 0.55, 0)
    X0, Y0, FW, FH = info["floor_x0"], info["floor_y0"], info["floor_w"], info["floor_h"]
    for c in range(cols + 1):
        x = min(X0 + int(c * cell), X0 + FW)
        cv2.line(out, (x, Y0), (x, Y0 + FH), (255, 255, 255), 1)
    for r in range(rows + 1):
        y = min(Y0 + int(r * cell), Y0 + FH)
        cv2.line(out, (X0, y), (X0 + FW, y), (255, 255, 255), 1)
    if letters:
        for k, code in cells.items():
            r, c = map(int, k.split(","))
            x0, y0, x1, y1 = cell_rect(info, grid_ft, r, c)
            cv2.putText(out, BY_CODE[code].letter, ((x0 + x1) // 2 - 7, (y0 + y1) // 2 + 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    for (r, c) in highlight:
        x0, y0, x1, y1 = cell_rect(info, grid_ft, r, c)
        cv2.rectangle(out, (x0 + 1, y0 + 1), (x1 - 1, y1 - 1), (0, 0, 255), 3)
    if tap is not None:
        x0, y0, x1, y1 = cell_rect(info, grid_ft, tap[0], tap[1])
        cv2.circle(out, ((x0 + x1) // 2, (y0 + y1) // 2), 14, (255, 160, 0), -1, cv2.LINE_AA)
        cv2.putText(out, "T", ((x0 + x1) // 2 - 7, (y0 + y1) // 2 + 7), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (255, 255, 255), 2, cv2.LINE_AA)
    if bearing is not None:
        draw_compass(out, bearing)
    return out


def area_table(info, grid_ft, cells):
    ppf = info["ppf"]
    total = info["floor_w"] * info["floor_h"] / ppf / ppf
    rows = []
    done = 0.0
    for t in TYPES:
        n, a = 0, 0.0
        for k, code in cells.items():
            if code != t.code:
                continue
            r, c = map(int, k.split(","))
            x0, y0, x1, y1 = cell_rect(info, grid_ft, r, c)
            n += 1
            a += (x1 - x0) * (y1 - y0) / ppf / ppf
        done += a
        rows.append({"Type": f"{t.emoji} {t.label}", "Cells": n, "Area (sq ft)": round(a, 1),
                     "% of floor": round(100 * a / total, 1)})
    rows.append({"Type": "⬛ Not assigned yet", "Cells": grid_dims(info, grid_ft)[0] * grid_dims(info, grid_ft)[1] - len(cells), "Area (sq ft)": round(total - done, 1),
                 "% of floor": round(100 * (total - done) / total, 1)})
    return rows


def export_dict(info, grid_ft, cells):
    cols, rows, _ = grid_dims(info, grid_ft)
    ppf = info["ppf"]
    fh_ft = info["floor_h"] / ppf
    lst = []
    for k, code in sorted(cells.items(), key=lambda kv: tuple(map(int, kv[0].split(",")))):
        r, c = map(int, k.split(","))
        x0, y0, x1, y1 = cell_rect(info, grid_ft, r, c)
        lst.append({"row": r, "col": c, "type": code,
                    "center_ft_from_A": [round(((x0 + x1) / 2 - info["floor_x0"]) / ppf, 2),
                                         round(fh_ft - ((y0 + y1) / 2 - info["floor_y0"]) / ppf, 2)],
                    "area_sqft": round((x1 - x0) * (y1 - y0) / ppf / ppf, 2)})
    return {"grid_ft": grid_ft, "cols": cols, "rows": rows,
            "floor_ft": [round(info["floor_w"] / ppf, 2), round(info["floor_h"] / ppf, 2)],
            "types": {t.code: t.label for t in TYPES}, "cells": lst}


def cells_csv(info, grid_ft, cells):
    d = export_dict(info, grid_ft, cells)
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(["row", "col", "type", "center_x_ft_from_A", "center_y_ft_from_A", "area_sqft"])
    for c in d["cells"]:
        wr.writerow([c["row"], c["col"], c["type"], *c["center_ft_from_A"], c["area_sqft"]])
    return buf.getvalue()
