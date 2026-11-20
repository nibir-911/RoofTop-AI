"""Draw the higher block, step walls, stair and door onto a top-view plan image. No Streamlit."""
import cv2
import numpy as np
import roofmodel as RM


def _px(info, roof, x, y):
    D = info["floor_h"] / info["ppf"]
    return int(round(info["floor_x0"] + x * info["ppf"])), int(round(info["floor_y0"] + (D - y) * info["ppf"]))


def overlay_roof(img, info, roof, grid_ft=2.0):
    """Returns a copy of img with the higher block tinted + outlined, step walls thick, openings marked."""
    out = img.copy()
    if not roof.get("block"):
        return out
    x0, y0, x1, y1 = RM.block_rect(roof)
    a, b = _px(info, roof, x0, y1), _px(info, roof, x1, y0)
    tint = out.copy()
    cv2.rectangle(tint, a, b, (90, 90, 90), -1)
    out = cv2.addWeighted(tint, 0.22, out, 0.78, 0)
    for i in range(a[0] - (b[1] - a[1]), b[0], 14):                          # light hatch = "higher"
        cv2.line(out, (max(i, a[0]), a[1] if i >= a[0] else a[1] + (a[0] - i)),
                 (min(i + (b[1] - a[1]), b[0]), b[1] if i + (b[1] - a[1]) <= b[0] else b[1] - (i + (b[1] - a[1]) - b[0])),
                 (230, 230, 230), 1, cv2.LINE_AA)
    for f in RM.step_faces(roof):                                            # step walls
        cv2.line(out, _px(info, roof, *f["p0"]), _px(info, roof, *f["p1"]), (30, 30, 30), 5, cv2.LINE_AA)
    for op in roof.get("openings", []):
        g = RM.opening_geometry(roof, op)
        if g is None:
            continue
        cx, cy = g["centre"]; nx, ny = g["normal"]; hw = g["width"] / 2
        depth = RM.LANDING_FT.get(g["kind"], 4.0)
        px, py = -ny, nx                                                      # along the wall
        pts = [(cx - px * hw, cy - py * hw), (cx + px * hw, cy + py * hw),
               (cx + px * hw + nx * depth, cy + py * hw + ny * depth), (cx - px * hw + nx * depth, cy - py * hw + ny * depth)]
        poly = np.array([_px(info, roof, *p) for p in pts], np.int32)
        col = (0, 200, 255) if g["kind"] == "outer_stair" else (60, 160, 60)
        cv2.polylines(out, [poly], True, col, 2, cv2.LINE_AA)
        if g["kind"] == "outer_stair":
            for t in np.linspace(0.1, 0.9, 6):
                s0 = _px(info, roof, cx - px * hw + nx * depth * t, cy - py * hw + ny * depth * t)
                s1 = _px(info, roof, cx + px * hw + nx * depth * t, cy + py * hw + ny * depth * t)
                cv2.line(out, s0, s1, col, 1, cv2.LINE_AA)
        m = _px(info, roof, cx + nx * depth / 2, cy + ny * depth / 2)
        cv2.putText(out, "STAIR UP" if g["kind"] == "outer_stair" else "DOOR", (m[0] - 32, m[1] + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(out, "STAIR UP" if g["kind"] == "outer_stair" else "DOOR", (m[0] - 32, m[1] + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1, cv2.LINE_AA)
    c = _px(info, roof, (x0 + x1) / 2, (y0 + y1) / 2)
    t = f"{roof['floors'][1]}th floor (+{roof.get('diff_ft', 10):g} ft)"
    cv2.putText(out, t, (c[0] - 70, c[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 3, cv2.LINE_AA)
    cv2.putText(out, t, (c[0] - 70, c[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 1, cv2.LINE_AA)
    return out
