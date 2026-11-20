"""Draws the garden plan (top view with icons) and a pseudo-3D impression. No Streamlit."""
import math, random
import cv2
import numpy as np
import roofcore as rc
import sprites as SP
import plants as PL

CAT_COLOR = {"vegetable": (70, 150, 60), "herb": (110, 190, 120), "fruit": (40, 100, 40),
             "flower": (90, 150, 80), "ornamental": (60, 120, 70)}


def hex_bgr(h):
    h = str(h).lstrip("#")
    if len(h) != 6:
        h = "66bb6a"
    return (int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16))


_SKIP = {"dwarf", "red", "boston", "bottle", "bitter", "malabar", "spring", "money", "snake"}


def short_label(name):
    w = name.replace("(", " ").replace(")", " ").split()
    pick = w[-1] if w[0].lower() in _SKIP and len(w) > 1 else w[0]
    return pick[:9]


def _outlined_text(img, text, org, scale=0.4):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)


def _glyph(img, cx, cy, size, cat, bloom, form=None):
    g = CAT_COLOR.get(cat, (80, 150, 80))
    if form == "climber":                      # vine on a trellis frame
        for dx in (-0.3, 0.3):
            cv2.line(img, (int(cx + dx * size), int(cy - 0.35 * size)), (int(cx + dx * size), int(cy + 0.35 * size)),
                     (90, 130, 170), 2, cv2.LINE_AA)
        for k in range(5):
            cv2.circle(img, (int(cx + ((k % 2) - 0.5) * 0.3 * size), int(cy + (k - 2) * 0.14 * size)),
                       int(size * 0.13), g, -1, cv2.LINE_AA)
            if cat == "flower":
                cv2.circle(img, (int(cx + ((k % 2) - 0.5) * 0.45 * size), int(cy + (k - 2) * 0.14 * size)),
                           int(size * 0.05), bloom, -1, cv2.LINE_AA)
        return
    if form == "hanging":
        for k in range(4):
            x = int(cx + (k - 1.5) * 0.18 * size)
            cv2.line(img, (x, int(cy - 0.2 * size)), (x, int(cy + 0.3 * size)), g, 3, cv2.LINE_AA)
            cv2.circle(img, (x, int(cy + 0.3 * size)), int(size * 0.07), bloom, -1, cv2.LINE_AA)
        return
    if cat == "flower":
        for k in range(6):
            a = k * math.pi / 3
            cv2.circle(img, (int(cx + math.cos(a) * size * 0.22), int(cy + math.sin(a) * size * 0.22)),
                       int(size * 0.17), bloom, -1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), int(size * 0.12), (0, 200, 255), -1, cv2.LINE_AA)
    elif cat == "fruit":
        cv2.circle(img, (cx, cy), int(size * 0.36), g, -1, cv2.LINE_AA)
        cv2.circle(img, (cx - int(size * .08), cy - int(size * .08)), int(size * 0.24), (60, 140, 60), -1, cv2.LINE_AA)
        for a in (0.5, 2.0, 3.6, 5.1):
            cv2.circle(img, (int(cx + math.cos(a) * size * .22), int(cy + math.sin(a) * size * .22)),
                       int(size * .06), bloom, -1, cv2.LINE_AA)
    elif cat == "herb":
        for dx, dy in ((-.16, .08), (.14, .1), (0, -.14)):
            cv2.circle(img, (int(cx + dx * size), int(cy + dy * size)), int(size * 0.17), g, -1, cv2.LINE_AA)
    elif cat == "ornamental":
        for k in range(5):
            a = k * 2 * math.pi / 5 - math.pi / 2
            cv2.ellipse(img, (int(cx + math.cos(a) * size * .16), int(cy + math.sin(a) * size * .16)),
                        (int(size * .2), int(size * .08)), math.degrees(a), 0, 360, g, -1, cv2.LINE_AA)
    else:                                            # vegetable
        cv2.circle(img, (cx, cy), int(size * 0.3), g, -1, cv2.LINE_AA)
        for a in (0.4, 2.2, 4.0):
            cv2.circle(img, (int(cx + math.cos(a) * size * .17), int(cy + math.sin(a) * size * .17)),
                       int(size * .06), bloom, -1, cv2.LINE_AA)


def render_plan(base, info, grid_ft, cells, placements, df, bearing=None, tap=None, labels=True, legend=True):
    out = base.copy()
    ov = out.copy()
    for k, code in cells.items():
        r, c = map(int, k.split(","))
        x0, y0, x1, y1 = rc.cell_rect(info, grid_ft, r, c)
        if code == "BLOCKED":
            cv2.rectangle(ov, (x0, y0), (x1, y1), (50, 50, 220), -1)
        elif code == "WALKWAY":
            cv2.rectangle(ov, (x0, y0), (x1, y1), (200, 200, 200), -1)
    out = cv2.addWeighted(ov, 0.45, out, 0.55, 0)
    X0, Y0, FW, FH = info["floor_x0"], info["floor_y0"], info["floor_w"], info["floor_h"]
    cols, rows, cell = rc.grid_dims(info, grid_ft)
    for c in range(cols + 1):
        x = min(X0 + int(c * cell), X0 + FW)
        cv2.line(out, (x, Y0), (x, Y0 + FH), (225, 225, 225), 1)
    for r in range(rows + 1):
        y = min(Y0 + int(r * cell), Y0 + FH)
        cv2.line(out, (X0, y), (X0 + FW, y), (225, 225, 225), 1)
    for p in placements:
        x0, y0, x1, y1 = rc.cell_rect(info, grid_ft, p["row"], p["col"])
        row = df.loc[p["plant_id"]]
        s = min(x1 - x0, y1 - y0)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        cv2.rectangle(out, (x0 + 4, y0 + 4), (x1 - 4, y1 - 4), (60, 95, 150), -1)
        cv2.rectangle(out, (x0 + 4, y0 + 4), (x1 - 4, y1 - 4), (30, 50, 90), 1)
        cv2.rectangle(out, (x0 + 8, y0 + 8), (x1 - 8, y1 - 8), (35, 50, 65), -1)
        _glyph(out, cx, cy - 3, s, p["category"], hex_bgr(row["bloom_hex"]), row["form"])
        if labels:
            t = short_label(row["name_en"])
            (tw, th), _ = cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
            _outlined_text(out, t, (cx - tw // 2, y1 - 8))
    if tap is not None:
        x0, y0, x1, y1 = rc.cell_rect(info, grid_ft, tap[0], tap[1])
        cv2.circle(out, ((x0 + x1) // 2, (y0 + y1) // 2), 12, (255, 160, 0), -1, cv2.LINE_AA)
        cv2.putText(out, "T", ((x0 + x1) // 2 - 6, (y0 + y1) // 2 + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (255, 255, 255), 2, cv2.LINE_AA)
    if bearing is not None:
        rc.draw_compass(out, bearing)
    if legend:
        counts = {}
        for p in placements:
            counts[p["plant_id"]] = counts.get(p["plant_id"], 0) + 1
        W = 300
        panel = np.full((out.shape[0], W, 3), 245, np.uint8)
        cv2.putText(panel, "Legend", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2, cv2.LINE_AA)
        y = 55
        for pid, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            row = df.loc[pid]
            cv2.rectangle(panel, (12, y - 14), (38, y + 8), (60, 95, 150), -1)
            _glyph(panel, 25, y - 3, 22, row["category"], hex_bgr(row["bloom_hex"]), row["form"])
            cv2.putText(panel, f"{row['name_en'][:24]} x{n}", (48, y + 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                        (30, 30, 30), 1, cv2.LINE_AA)
            y += 28
            if y > out.shape[0] - 90:
                break
        cv2.rectangle(panel, (12, out.shape[0] - 70), (38, out.shape[0] - 48), (50, 50, 220), -1)
        cv2.putText(panel, "Blocked", (48, out.shape[0] - 53), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 30, 30), 1, cv2.LINE_AA)
        cv2.rectangle(panel, (12, out.shape[0] - 40), (38, out.shape[0] - 18), (200, 200, 200), -1)
        cv2.putText(panel, "Walkway", (48, out.shape[0] - 23), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 30, 30), 1, cv2.LINE_AA)
        out = np.hstack([out, panel])
    return out


# ------------------------------------------------------------------ pseudo-3D

STAGE_K = {"planting": 0.30, "mid": 0.65, "mature": 1.0}
STAGE_LABEL = {"planting": "Planting day", "mid": "About 3 months", "mature": "Mature"}
FORM_COLOR = {"patch": (90, 170, 90), "bush": (70, 150, 60), "climber": (60, 140, 70),
              "hanging": (80, 160, 100), "shrub": (45, 110, 45), "succulent": (100, 160, 110)}


def _blob(canvas, cen, rx, ry, col):
    for k, (scale, shade) in enumerate(((1.0, 0.65), (0.82, 0.9), (0.6, 1.15))):
        c = tuple(int(min(255, v * shade)) for v in col)
        cv2.ellipse(canvas, (int(cen[0] - k * rx * 0.05), int(cen[1] - k * ry * 0.06)),
                    (max(2, int(rx * scale)), max(2, int(ry * scale))), 0, 0, 360, c, -1, cv2.LINE_AA)


def _dots(canvas, cen, rx, ry, n, col, rad, rnd):
    for _ in range(n):
        a, rr = rnd.random() * 2 * math.pi, math.sqrt(rnd.random()) * 0.8
        cv2.circle(canvas, (int(cen[0] + math.cos(a) * rx * rr), int(cen[1] + math.sin(a) * ry * rr)),
                   max(2, int(rad)), col, -1, cv2.LINE_AA)


def draw_plant_3d(canvas, Pf, X, Y, bh, row, bloom, rnd, k, flowering):
    """Draw one plant by growth form (stylised). k = growth scale 0..1."""
    form = row["form"]
    cat = row["category"]
    d = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
    h = max(min(float(row["height_ft"]), 8.0) * k, 0.35)
    rad = min(max(float(row["canopy_ft"]) * max(k, 0.45) / 2, 0.25), 0.85)
    g = FORM_COLOR.get(form, (80, 150, 80))
    base = Pf(X, Y, bh)
    rx0 = d(Pf(X + rad, Y, bh), base)
    if form == "patch":
        cen = Pf(X, Y, bh + max(h, 0.3) * 0.4)
        _blob(canvas, cen, rx0 * 1.05, rx0 * 0.5, g)
        if flowering and cat == "flower":
            _dots(canvas, cen, rx0, rx0 * 0.45, 8, bloom, rx0 * 0.12, rnd)
    elif form == "climber":
        top = Pf(X, Y, bh + h)
        for dx in (-0.6, 0.6):
            a, b = Pf(X + dx, Y, bh), Pf(X + dx, Y, bh + h)
            cv2.line(canvas, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (80, 115, 150), 2, cv2.LINE_AA)
        for j in range(1, 4):
            a, b = Pf(X - 0.6, Y, bh + h * j / 4), Pf(X + 0.6, Y, bh + h * j / 4)
            cv2.line(canvas, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (80, 115, 150), 1, cv2.LINE_AA)
        n = max(3, int(9 * k))
        for j in range(n):
            cen = Pf(X + ((j % 3) - 1) * 0.35, Y, bh + h * (0.15 + 0.8 * j / n))
            _blob(canvas, cen, rx0 * 0.55 + 3, rx0 * 0.35 + 3, g)
            if flowering and cat == "flower" and j % 2 == 0:
                cv2.circle(canvas, (int(cen[0] + 4), int(cen[1])), max(3, int(rx0 * 0.12)), bloom, -1, cv2.LINE_AA)
        if cat == "vegetable" and k >= 0.65:                     # hanging gourds / beans
            for dx in (-0.3, 0.25):
                c0 = Pf(X + dx, Y, bh + h * 0.45)
                cv2.ellipse(canvas, (int(c0[0]), int(c0[1])), (max(3, int(rx0 * 0.12)), max(6, int(rx0 * 0.4))), 0, 0,
                            360, (150, 215, 170), -1, cv2.LINE_AA)
    elif form == "hanging":
        _blob(canvas, Pf(X, Y, bh + 0.25), rx0, rx0 * 0.4, g)
        for j in range(-2, 3):
            a, b = Pf(X + j * 0.28, Y - 0.8, bh + 0.35), Pf(X + j * 0.28, Y - 0.8, bh - 0.3 - 0.4 * k)
            cv2.line(canvas, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), g, 3, cv2.LINE_AA)
            if flowering:
                cv2.circle(canvas, (int(b[0]), int(b[1])), max(3, int(rx0 * 0.1)), bloom, -1, cv2.LINE_AA)
    elif form == "shrub":
        a, b = base, Pf(X, Y, bh + h * 0.45)
        cv2.line(canvas, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (40, 70, 100), max(3, int(rx0 * 0.12)), cv2.LINE_AA)
        cen = Pf(X, Y, bh + h * 0.72)
        rxs = d(Pf(X + rad * 1.1, Y, bh + h * 0.72), cen)
        rys = max(rxs * 0.8, d(Pf(X, Y, bh + h), Pf(X, Y, bh + h * 0.4)) / 2)
        _blob(canvas, cen, rxs, rys, g)
        if flowering or (cat == "fruit" and k >= 0.65):
            _dots(canvas, cen, rxs, rys, 10, bloom, rxs * 0.12, rnd)
    elif form == "succulent":
        for j in range(7):
            ang = -math.pi / 2 + (j - 3) * 0.33
            tip = (base[0] + math.cos(ang) * rx0 * 0.9, base[1] + math.sin(ang) * max(h, 0.6) * rx0 * 0.9 * 1.4 - 2)
            cv2.line(canvas, (int(base[0]), int(base[1])), (int(tip[0]), int(tip[1])), g, max(3, int(rx0 * 0.2)), cv2.LINE_AA)
    else:                                                          # bush
        cen = Pf(X, Y, bh + max(h, 0.8) * 0.5)
        ry = max(rx0 * 0.75, d(Pf(X, Y, bh + max(h, 0.8)), base) / 2)
        _blob(canvas, cen, rx0, ry, g)
        if flowering and cat == "flower":
            _dots(canvas, cen, rx0, ry, 16, bloom, rx0 * 0.14, rnd)
        elif cat in ("vegetable", "fruit") and k >= 0.65:
            _dots(canvas, cen, rx0, ry, 5, bloom, rx0 * 0.1, rnd)

def render_pseudo3d(floor_img, strips, placements, df, info, grid_ft, wall_ft, bearing=None,
                    out_w=1200, out_h=780, cam_h_ft=6.0, stage="mature", month=None, sprites_base=None):
    """Perspective impression from the Side 1 end looking towards Side 3. Illustrative only."""
    ppf = info["ppf"]
    Wf, Hf = info["floor_w"] / ppf, info["floor_h"] / ppf
    C = np.array([Wf / 2, -0.95 * max(Wf, Hf), cam_h_ft])
    T = np.array([Wf / 2, Hf * 0.5, 0.0])
    f = T - C
    f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)

    def raw(x, y, z):
        d = np.array([x, y, z]) - C
        zc = d @ f
        return np.array([(d @ r) / zc, (d @ u) / zc])

    keys = [raw(x, y, z) for x in (0, Wf) for y in (0, Hf) for z in (0, wall_ft, 8.5)]
    ks = np.array(keys)
    mn, mx = ks.min(0), ks.max(0)
    s = min(out_w * 0.94 / (mx[0] - mn[0]), out_h * 0.92 / (mx[1] - mn[1]))
    ox = (out_w - (mx[0] - mn[0]) * s) / 2
    oy = (out_h - (mx[1] - mn[1]) * s) / 2

    def P(x, y, z):
        q = raw(x, y, z)
        return (ox + (q[0] - mn[0]) * s, oy + (mx[1] - q[1]) * s)

    canvas = np.zeros((out_h, out_w, 3), np.uint8)
    top, bot = np.array([235, 205, 160], float), np.array([250, 245, 238], float)
    for yy in range(out_h):
        canvas[yy, :] = (top + (bot - top) * yy / out_h).astype(np.uint8)

    def warp(src, quad):
        h, w = src.shape[:2]
        M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(quad))
        warped = cv2.warpPerspective(src, M, (out_w, out_h), flags=cv2.INTER_LINEAR)
        m = np.zeros((out_h, out_w), np.uint8)
        cv2.fillConvexPoly(m, np.int32(quad), 255)
        canvas[m > 0] = warped[m > 0]

    s1, s2, s3, s4 = strips
    warp(s3[:, ::-1], [P(0, Hf, wall_ft), P(Wf, Hf, wall_ft), P(Wf, Hf, 0), P(0, Hf, 0)])       # back wall
    warp(s4, [P(0, Hf, wall_ft), P(0, 0, wall_ft), P(0, 0, 0), P(0, Hf, 0)])                    # left wall
    warp(s2, [P(Wf, 0, wall_ft), P(Wf, Hf, wall_ft), P(Wf, Hf, 0), P(Wf, 0, 0)])                # right wall
    warp(floor_img, [P(0, Hf, 0), P(Wf, Hf, 0), P(Wf, 0, 0), P(0, 0, 0)])                       # floor

    def dist(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    X0, Y0 = info["floor_x0"], info["floor_y0"]
    items = []
    for p in placements:
        x0, y0, x1, y1 = rc.cell_rect(info, grid_ft, p["row"], p["col"])
        X = ((x0 + x1) / 2 - X0) / ppf
        Y = Hf - ((y0 + y1) / 2 - Y0) / ppf
        items.append((Y, X, p))
    items.sort(key=lambda t: -t[0])                       # far first
    half, bh = 0.8, 0.6
    used = {"sprite": 0, "shape": 0}
    for Y, X, p in items:
        row = df.loc[p["plant_id"]]
        rnd = random.Random(f"{p['row']}-{p['col']}")
        bloom = hex_bgr(row["bloom_hex"])
        # planter box
        front = [P(X - half, Y - half, 0), P(X + half, Y - half, 0), P(X + half, Y - half, bh), P(X - half, Y - half, bh)]
        cv2.fillConvexPoly(canvas, np.int32(front), (60, 95, 150), cv2.LINE_AA)
        side_x = X + half if X < C[0] else X - half
        side = [P(side_x, Y - half, 0), P(side_x, Y + half, 0), P(side_x, Y + half, bh), P(side_x, Y - half, bh)]
        cv2.fillConvexPoly(canvas, np.int32(side), (45, 72, 118), cv2.LINE_AA)
        topf = [P(X - half, Y - half, bh), P(X + half, Y - half, bh), P(X + half, Y + half, bh), P(X - half, Y + half, bh)]
        cv2.fillConvexPoly(canvas, np.int32(topf), (35, 50, 65), cv2.LINE_AA)
        k = STAGE_K.get(stage, 1.0)
        bl = str(row["bloom_months"]).lower()
        flowering = k >= 0.65 and bl != "none" and (month is None or PL.in_bloom(row, month))
        spr = SP.load_sprite(p["plant_id"], stage, sprites_base)
        if spr is not None:
            hft = max(min(float(row["height_ft"]), 8.0) * k, 0.4)
            top, bot = P(X, Y, bh + hft), P(X, Y, bh)
            SP.paste_rgba(canvas, spr, bot[0], bot[1] + 4, abs(bot[1] - top[1]))
            used["sprite"] += 1
        else:
            draw_plant_3d(canvas, P, X, Y, bh, row, bloom, rnd, k, flowering)
            used["shape"] += 1
    if used["sprite"] + used["shape"] != len(placements):                  # control check
        raise RuntimeError("3D render drew a different number of plants than the layout has")
    cv2.putText(canvas, STAGE_LABEL.get(stage, stage) + (f" · {PL.MONTH_NAMES[month - 1]}" if month else ""),
                (14, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 60, 60), 1, cv2.LINE_AA)
    cv2.putText(canvas, "Illustrative impression - not to scale", (14, out_h - 14), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (60, 60, 60), 1, cv2.LINE_AA)
    cv2.putText(canvas, "View from the Side 1 end, looking towards Side 3", (14, 28), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (60, 60, 60), 1, cv2.LINE_AA)
    if bearing is not None:
        cv2.putText(canvas, f"Side 3 (far wall) faces {rc.compass_name((bearing + 180) % 360)}", (14, 52),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 60, 60), 1, cv2.LINE_AA)
    return canvas
