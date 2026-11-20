"""Roof geometry for one- or two-level roofs. No Streamlit.
Plan coordinates (feet): corner A=(0,0), x to the right, y upward. B=(W,0), C=(W,D), D=(0,D).
Grid: 2 ft cells keyed "row,col"; row 0 = top of the plan (y=D), col 0 = left (x=0).
Level 1 = main roof (e.g. 5th floor). Level 2 = higher block in one corner (e.g. 6th floor, stair house below).
roof = {"W":..,"D":..,"block":None | {"w":..,"d":..,"corner":"A|B|C|D"},"diff_ft":10,"floors":[5,6],
        "openings":[{"kind":"outer_stair"|"door","face":"N|S|E|W","pos_ft":..,"width_ft":3}]}"""
import math

EPS = 1e-6
LANDING_FT = {"door": 4.0, "outer_stair": 6.0}          # keep-clear depth in front of the wall (ft)
STAIR_RISE_STEPS = 10                                       # steep outer stair: 10 steps, about 6 ft run
SIDE_NAMES = {1: "A→B (bottom)", 2: "B→C (right)", 3: "C→D (top)", 4: "D→A (left)"}


def new_roof(W=20.0, D=15.0, block=None, diff_ft=10.0, floors=(5, 6), openings=None):
    return {"W": float(W), "D": float(D), "block": block, "diff_ft": float(diff_ft), "floors": list(floors),
            "openings": list(openings or [])}


def block_rect(roof):
    """(x0, y0, x1, y1) of the higher block in plan feet, or None."""
    b = roof.get("block")
    if not b:
        return None
    W, D, w, d = roof["W"], roof["D"], b["w"], b["d"]
    c = b["corner"]
    x0 = 0.0 if c in ("A", "D") else W - w
    y0 = 0.0 if c in ("A", "B") else D - d
    return (x0, y0, x0 + w, y0 + d)


def validate(roof):
    """List of human-readable problems (empty if the roof is valid)."""
    errs = []
    W, D = roof["W"], roof["D"]
    if W <= 0 or D <= 0:
        errs.append("Roof width and depth must be positive.")
    b = roof.get("block")
    if b:
        if b.get("corner") not in ("A", "B", "C", "D"):
            errs.append("Block corner must be A, B, C or D.")
        if b["w"] <= 0 or b["d"] <= 0:
            errs.append("Block width and depth must be positive.")
        if b["w"] >= W and b["d"] >= D:
            errs.append("The higher block cannot cover the whole roof.")
        if b["w"] > W or b["d"] > D:
            errs.append("The higher block must fit inside the roof.")
    return errs


def level_polygon(roof, level):
    """Outline (list of (x, y)) of a level. Level 1 is an L-shape when a block exists."""
    W, D = roof["W"], roof["D"]
    r = block_rect(roof)
    if level == 2:
        return None if r is None else [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    if r is None:
        return [(0, 0), (W, 0), (W, D), (0, D)]
    x0, y0, x1, y1 = r
    c = roof["block"]["corner"]
    if c == "C":
        return [(0, 0), (W, 0), (W, y0), (x0, y0), (x0, D), (0, D)]
    if c == "B":
        return [(0, 0), (x0, 0), (x0, y1), (W, y1), (W, D), (0, D)]
    if c == "A":
        return [(0, y1), (x1, y1), (x1, 0), (W, 0), (W, D), (0, D)]
    return [(0, 0), (W, 0), (W, D), (x1, D), (x1, y0), (0, y0)]          # corner D


def areas(roof):
    r = block_rect(roof)
    total = roof["W"] * roof["D"]
    a2 = 0.0 if r is None else (r[2] - r[0]) * (r[3] - r[1])
    return {1: total - a2, 2: a2, "total": total}


# ------------------------------------------------------------------ grid
def grid_dims(roof, grid_ft=2.0):
    return math.ceil(roof["D"] / grid_ft - EPS), math.ceil(roof["W"] / grid_ft - EPS)      # rows, cols


def cell_extent(roof, r, c, grid_ft=2.0):
    """(x0, y0, x1, y1) of a cell in plan feet (edge cells may be smaller)."""
    x0, x1 = c * grid_ft, min((c + 1) * grid_ft, roof["W"])
    y1, y0 = roof["D"] - r * grid_ft, max(roof["D"] - (r + 1) * grid_ft, 0.0)
    return (x0, y0, x1, y1)


def cell_center(roof, r, c, grid_ft=2.0):
    x0, y0, x1, y1 = cell_extent(roof, r, c, grid_ft)
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def cell_area(roof, r, c, grid_ft=2.0):
    x0, y0, x1, y1 = cell_extent(roof, r, c, grid_ft)
    return (x1 - x0) * (y1 - y0)


def level_of_cell(roof, r, c, grid_ft=2.0):
    br = block_rect(roof)
    if br is None:
        return 1
    x, y = cell_center(roof, r, c, grid_ft)
    return 2 if (br[0] <= x <= br[2] and br[1] <= y <= br[3]) else 1


def level_cells(roof, grid_ft=2.0):
    rows, cols = grid_dims(roof, grid_ft)
    out = {1: set(), 2: set()}
    for r in range(rows):
        for c in range(cols):
            out[level_of_cell(roof, r, c, grid_ft)].add((r, c))
    return out


def key(rc):
    return f"{rc[0]},{rc[1]}"


def parse_key(k):
    r, c = k.split(",")
    return int(r), int(c)


# ------------------------------------------------------------------ faces, openings
def step_faces(roof):
    """Faces of the higher block that look onto the lower roof. face = direction the wall faces (N/S/E/W)."""
    br = block_rect(roof)
    if br is None:
        return []
    x0, y0, x1, y1 = br
    W, D = roof["W"], roof["D"]
    out = []
    if y0 > EPS:
        out.append({"face": "S", "p0": (x0, y0), "p1": (x1, y0), "normal": (0, -1), "length": x1 - x0})
    if y1 < D - EPS:
        out.append({"face": "N", "p0": (x0, y1), "p1": (x1, y1), "normal": (0, 1), "length": x1 - x0})
    if x0 > EPS:
        out.append({"face": "W", "p0": (x0, y0), "p1": (x0, y1), "normal": (-1, 0), "length": y1 - y0})
    if x1 < W - EPS:
        out.append({"face": "E", "p0": (x1, y0), "p1": (x1, y1), "normal": (1, 0), "length": y1 - y0})
    return out


def opening_geometry(roof, op):
    """Centre point on the step wall, outward normal and width. None if the face does not exist."""
    f = next((f for f in step_faces(roof) if f["face"] == op["face"]), None)
    if f is None:
        return None
    pos = min(max(op["pos_ft"], op["width_ft"] / 2), f["length"] - op["width_ft"] / 2)
    if f["face"] in ("N", "S"):
        centre = (f["p0"][0] + pos, f["p0"][1])
    else:
        centre = (f["p0"][0], f["p0"][1] + pos)
    return {"kind": op["kind"], "face": f["face"], "centre": centre, "normal": f["normal"],
            "width": op["width_ft"], "pos_ft": pos}


def _rect(centre, normal, hw, depth):
    """Rectangle that starts at the wall point `centre` and extends `depth` ft along `normal`,
    with half-width `hw` across it. Returns (x0, y0, x1, y1)."""
    cx, cy = centre
    nx, ny = normal
    if nx == 0:
        ya, yb = sorted((cy, cy + ny * depth))
        return (cx - hw, ya, cx + hw, yb)
    xa, xb = sorted((cx, cx + nx * depth))
    return (xa, cy - hw, xb, cy + hw)


def opening_cells(roof, grid_ft=2.0):
    """{ "r,c": reason } for cells that must stay clear: the landing in front of a door / stair on the lower
    roof, and the entry cell at the top of an outer stair on the upper roof."""
    out = {}
    rows, cols = grid_dims(roof, grid_ft)
    for op in roof.get("openings", []):
        g = opening_geometry(roof, op)
        if g is None:
            continue
        hw = max(g["width"] / 2, grid_ft / 2 + 0.01)
        land = _rect(g["centre"], g["normal"], hw, LANDING_FT.get(g["kind"], 4.0))
        entry = _rect(g["centre"], (-g["normal"][0], -g["normal"][1]), hw, grid_ft)
        for r in range(rows):
            for c in range(cols):
                x, y = cell_center(roof, r, c, grid_ft)
                lv = level_of_cell(roof, r, c, grid_ft)
                if lv == 1 and land[0] <= x <= land[2] and land[1] <= y <= land[3]:
                    out[key((r, c))] = f"{g['kind']} landing"
                if lv == 2 and g["kind"] == "outer_stair" and entry[0] <= x <= entry[2] and entry[1] <= y <= entry[3]:
                    out[key((r, c))] = "stair top entry"
    return out


def has_outer_stair(roof):
    return any(op["kind"] == "outer_stair" and opening_geometry(roof, op) is not None
               for op in roof.get("openings", []))


def effective_cells(roof, cells, grid_ft=2.0):
    """User cells plus WALKWAY forced by stair/door landings (does not change the user's own dict)."""
    out = dict(cells)
    for k in opening_cells(roof, grid_ft):
        out[k] = "WALKWAY"
    return out


# ------------------------------------------------------------------ railings / edges
def outer_side_segments(roof):
    """Outer railing pieces on the four sides of the bounding rectangle: [{side, t0, t1, level}].
    side 1 = A→B, 2 = B→C, 3 = C→D, 4 = D→A; t runs along that walking direction (0..1)."""
    W, D = roof["W"], roof["D"]
    br = block_rect(roof)
    lengths = {1: W, 2: D, 3: W, 4: D}
    segs = []
    for side in (1, 2, 3, 4):
        L = lengths[side]
        if br is None:
            segs.append({"side": side, "t0": 0.0, "t1": 1.0, "level": 1})
            continue
        x0, y0, x1, y1 = br
        if side == 1 and y0 < EPS:
            a, b = x0 / W, x1 / W
        elif side == 2 and x1 > W - EPS:
            a, b = y0 / D, y1 / D
        elif side == 3 and y1 > D - EPS:
            a, b = (W - x1) / W, (W - x0) / W
        elif side == 4 and x0 < EPS:
            a, b = (D - y1) / D, (D - y0) / D
        else:
            segs.append({"side": side, "t0": 0.0, "t1": 1.0, "level": 1})
            continue
        for t0, t1, lv in ((0.0, a, 1), (a, b, 2), (b, 1.0, 1)):
            if t1 - t0 > 1e-6:
                segs.append({"side": side, "t0": t0, "t1": t1, "level": lv})
    return segs


def railing_cells(roof, level, grid_ft=2.0):
    """Cells of a level that touch a railing/parapet (climbers and hanging plants may use these)."""
    rows, cols = grid_dims(roof, grid_ft)
    lc = level_cells(roof, grid_ft)
    mine = lc[level]
    out = set()
    for (r, c) in mine:
        if level == 1:
            if r in (0, rows - 1) or c in (0, cols - 1):
                out.add((r, c))
        else:
            for nb in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if nb not in mine:
                    out.add((r, c))
                    break
    return out
