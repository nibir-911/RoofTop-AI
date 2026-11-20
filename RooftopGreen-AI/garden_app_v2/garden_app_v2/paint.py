"""Turns a drawn shape (brush stroke, lasso, polygon, rectangle, circle) into the set of grid cells it covers.
Pure Python (numpy + OpenCV), no Streamlit. Shapes are in IMAGE PIXELS; the brush radius is in feet.
shape = {"tool": "brush"|"lasso"|"polygon"|"rect"|"circle", "points": [[x, y], ...], "radius_ft": 2.0}
A cell counts when its centre pixel is inside the shape (mode "center") or >= 50% of it is covered ("half")."""
import cv2
import numpy as np
import roofcore as rc

TOOLS = ("brush", "lasso", "polygon", "rect", "circle")


def shape_mask(shape, info):
    """Boolean-ish uint8 mask (255 inside) the size of the plan image."""
    H, W = int(info["image_h"]), int(info["image_w"])
    m = np.zeros((H, W), np.uint8)
    tool = shape.get("tool")
    pts = np.round(np.array(shape.get("points", []), float)).astype(int)
    if tool not in TOOLS or len(pts) == 0:
        return m
    if tool == "brush":
        r = max(1, int(round(float(shape.get("radius_ft", 2.0)) * info["ppf"])))
        for i in range(len(pts) - 1):
            cv2.line(m, tuple(int(v) for v in pts[i]), tuple(int(v) for v in pts[i + 1]), 255, 2 * r + 1)
        for p in pts:
            cv2.circle(m, (int(p[0]), int(p[1])), r, 255, -1)
    elif tool in ("lasso", "polygon"):
        if len(pts) >= 3:
            cv2.fillPoly(m, [pts.reshape(-1, 1, 2)], 255)
    elif tool == "rect":
        if len(pts) >= 2:
            cv2.rectangle(m, tuple(int(v) for v in pts[0]), tuple(int(v) for v in pts[1]), 255, -1)
    elif tool == "circle":
        if len(pts) >= 2:
            rad = int(round(float(np.hypot(*(pts[1] - pts[0])))))
            cv2.circle(m, (int(pts[0][0]), int(pts[0][1])), rad, 255, -1)
    return m


def select(shape, info, grid_ft=2.0, mode="center"):
    """Set of "row,col" keys covered by the shape."""
    m = shape_mask(shape, info)
    H, W = m.shape
    cols, rows, _ = rc.grid_dims(info, grid_ft)
    out = set()
    for r in range(rows):
        for c in range(cols):
            x0, y0, x1, y1 = rc.cell_rect(info, grid_ft, r, c)
            if mode == "half":
                sub = m[max(y0, 0):min(y1, H), max(x0, 0):min(x1, W)]
                hit = sub.size > 0 and (sub.mean() / 255.0) >= 0.5
            else:
                cx, cy = min(max((x0 + x1) // 2, 0), W - 1), min(max((y0 + y1) // 2, 0), H - 1)
                hit = m[cy, cx] > 0
            if hit:
                out.add(f"{r},{c}")
    return out


def area_sqft(info, grid_ft, keys):
    total = 0.0
    for k in keys:
        r, c = map(int, k.split(","))
        x0, y0, x1, y1 = rc.cell_rect(info, grid_ft, r, c)
        total += (x1 - x0) * (y1 - y0) / info["ppf"] / info["ppf"]
    return total


def apply_selection(cells, selected, code, overwrite=True, allowed=None):
    """New cells dict with `selected` set to `code` (or erased when code is None).
    allowed: optional set of keys the user may change (e.g. cells that exist on the roof)."""
    out = dict(cells)
    n = 0
    for k in selected:
        if allowed is not None and k not in allowed:
            continue
        if code is None:
            if k in out:
                del out[k]
                n += 1
        elif overwrite or k not in out:
            if out.get(k) != code:
                out[k] = code
                n += 1
    return out, n
