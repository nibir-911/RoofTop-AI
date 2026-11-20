"""Rule-based garden layout generator, metrics and bill of materials. No Streamlit, no LLM."""
import random
import pandas as pd
import plants as P
import roofmodel as RM

VARIANTS = {
    "Productive": dict(fill=0.70, maint=0.0, desc="Most harvest: vegetables, herbs, fruit.",
                       bias={"vegetable": 1.6, "herb": 1.3, "fruit": 1.3, "flower": 0.5, "ornamental": 0.4}),
    "Colorful": dict(fill=0.65, maint=0.2, desc="Flowers and ornamentals first, some herbs.",
                     bias={"flower": 1.7, "ornamental": 1.3, "vegetable": 0.5, "herb": 0.7, "fruit": 0.8}),
    "Balanced": dict(fill=0.50, maint=0.8, desc="A mix, hardier plants, more open space, less work.",
                     bias={}),
}
CAT_ORDER = ["fruit", "vegetable", "herb", "flower", "ornamental"]
EFFORT_H = {"low": 0.15, "med": 0.30, "high": 0.50}        # hours per planter per week (indicative)


def _alloc(n, shares):
    raw = {k: n * v for k, v in shares.items()}
    out = {k: int(v) for k, v in raw.items()}
    left = n - sum(out.values())
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[:left]:
        out[k] += 1
    return out


def _neighbors(rc):
    r, c = rc
    return [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]


def _unreachable(placed, rows, cols, blocked):
    """Planters with no open neighbour in the main walkable area (cannot be reached by hand)."""
    free = {(r, c) for r in range(rows) for c in range(cols) if (r, c) not in blocked and (r, c) not in placed}
    seen, best = set(), set()
    for s in free:
        if s in seen:
            continue
        comp, stack = set(), [s]
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp.add(x)
            stack.extend(n for n in _neighbors(x) if n in free and n not in comp)
        seen |= comp
        if len(comp) > len(best):
            best = comp
    return [p for p in placed if not any(n in best for n in _neighbors(p))]


def _enforce_access(placed, rows, cols, blocked):
    """Safety net: remove planters that cannot be reached by hand."""
    removed = []
    while True:
        free = {(r, c) for r in range(rows) for c in range(cols) if (r, c) not in blocked and (r, c) not in placed}
        seen, best = set(), set()
        for s in free:
            if s in seen:
                continue
            comp, stack = set(), [s]
            while stack:
                x = stack.pop()
                if x in comp:
                    continue
                comp.add(x)
                stack.extend(n for n in _neighbors(x) if n in free and n not in comp)
            seen |= comp
            if len(comp) > len(best):
                best = comp
        bad = [p for p in placed if not any(n in best for n in _neighbors(p))]
        if not bad:
            return removed
        for p in bad:
            placed.discard(p)
            removed.append(p)


def edge_cells(rows, cols):
    """Cells touching a railing/wall (outer ring of the grid)."""
    return {(r, c) for r in range(rows) for c in range(cols) if r in (0, rows - 1) or c in (0, cols - 1)}


def generate(cells, cols, rows, df, prefs, month, variant, north_vec, tap=None, seed=0, max_species=3,
             domain=None, edge=None):
    """cells: {"r,c": TYPE}. Returns dict(placements, notes). north_vec: (dx, dy) in image coords.
    Climbers and hanging plants (needs_wall) are only placed on edge cells next to a railing."""
    cfg = VARIANTS[variant]
    rng = random.Random(f"{seed}-{variant}")
    zone_of, blocked = {}, set()
    for k, z in cells.items():
        rc = tuple(map(int, k.split(",")))
        if z in P.PLANT_ZONES:
            zone_of[rc] = z
        elif z == "BLOCKED":
            blocked.add(rc)
    if domain is not None:                      # only this level's cells exist; everything else is a wall
        blocked |= {(r, c) for r in range(rows) for c in range(cols) if (r, c) not in domain}
        zone_of = {rc: z for rc, z in zone_of.items() if rc in domain}
    notes = []
    if not zone_of:
        return {"placements": [], "notes": ["No planting cells (sun/shade types) are assigned in the grid."],
                "variant": variant}

    edge = edge if edge is not None else edge_cells(rows, cols)
    mix = P.normalized_mix(prefs, cfg["bias"])
    n_total = max(1, int(round(cfg["fill"] * len(zone_of))))
    targets = _alloc(n_total, mix)

    best = {}
    for z in set(zone_of.values()):
        cdf = P.candidates_for_zone(df, z, month, prefs, bias=cfg["bias"], maint_extra=cfg["maint"])
        for _, r in cdf.iterrows():
            e = best.setdefault(r["id"], [r["Score"], set()])
            e[0] = max(e[0], r["Score"])
            e[1].add(z)

    free = set(zone_of)
    chosen = {}
    nx, ny = north_vec
    wall = lambda pid: bool(df.loc[pid, "needs_wall"])

    def avail_for(pid):
        zones = best[pid][1]
        return [rc for rc in free if zone_of[rc] in zones and (not wall(pid) or rc in edge)]

    def place(pid, count):
        row = df.loc[pid]
        center = (float(row["sun_min"]) + float(row["sun_max"])) / 2

        def key(rc):
            dot = (rc[1] + 0.5) * nx + (rc[0] + 0.5) * ny              # larger = more north
            if float(row["height_ft"]) >= 3:
                return (-dot, rng.random())
            tapd = 0.0
            if tap is not None and row["water"] == "high":
                tapd = abs(rc[0] - tap[0]) + abs(rc[1] - tap[1])
            return (round(abs(P.ZONE_HOURS[zone_of[rc]] - center), 1), tapd, dot, rng.random())

        done = 0
        for rc in sorted(avail_for(pid), key=key):
            if done >= count:
                break
            if _unreachable(set(chosen) | {rc}, rows, cols, blocked):
                continue                                              # would block hand access
            free.discard(rc)
            chosen[rc] = pid
            done += 1
        return done

    for cat in CAT_ORDER:
        n = targets.get(cat, 0)
        if n <= 0:
            continue
        pool = sorted(((e[0] + rng.random() * 0.3, pid) for pid, e in best.items()
                       if df.loc[pid, "category"] == cat), reverse=True)
        if not pool:
            notes.append(f"No suitable {cat} plants for your zones and month; that share was skipped.")
            continue
        picks, wall_used = [], 0
        for _, pid in pool:
            if len(picks) >= min(max_species, n):
                break
            if wall(pid):
                if wall_used >= 1 or not avail_for(pid):
                    continue
                wall_used += 1
            picks.append(pid)
        if not picks:
            picks = [pool[0][1]]
        picks.sort(key=lambda pid: -float(df.loc[pid, "height_ft"]))
        shares = {pid: n // len(picks) + (1 if i < n % len(picks) else 0) for i, pid in enumerate(picks)}
        deficit = 0
        for pid in picks:
            want = min(shares[pid], 4) if wall(pid) else shares[pid]        # keep railing cells shared
            deficit += shares[pid] - want
            got = place(pid, want)
            deficit += want - got
        if deficit > 0:                                                       # refill with non-wall plants
            for _, pid in pool:
                if deficit <= 0:
                    break
                if wall(pid):
                    continue
                deficit -= place(pid, deficit)
        if deficit > 0:
            notes.append(f"{deficit} {cat} planter(s) could not be placed (no compatible free cells).")

    placed = set(chosen)
    removed = _enforce_access(placed, rows, cols, blocked)
    if removed:
        notes.append(f"{len(removed)} planter(s) were removed because you could not reach them by hand.")
    placements = []
    for rc in sorted(placed):
        pid = chosen[rc]
        row = df.loc[pid]
        placements.append({"row": rc[0], "col": rc[1], "plant_id": pid, "name": row["name_en"],
                           "category": row["category"], "form": row["form"], "zone": zone_of[rc]})
    nwall = sum(1 for p in placements if wall(p["plant_id"]))
    if nwall:
        notes.append(f"{nwall} climber/hanging planter(s) were placed along railings (they need a wall or railing).")
    return {"placements": placements, "notes": notes, "variant": variant}


def shade_conflicts(placements, df, north_vec):
    """Count short sun-loving plants sitting right on the shadow side of a tall plant.
    At Bangladesh latitudes the midday sun is in the south, so shadows fall towards north."""
    nx, ny = north_vec
    dr, dc = (int(round(ny)), 0) if abs(ny) >= abs(nx) else (0, int(round(nx)))
    pos = {(p["row"], p["col"]): p["plant_id"] for p in placements}
    n = 0
    for (r, c), pid in pos.items():
        tall = df.loc[pid]
        if float(tall["height_ft"]) < 4:
            continue
        other = pos.get((r + dr, c + dc))
        if other is None:
            continue
        o = df.loc[other]
        if float(o["height_ft"]) <= float(tall["height_ft"]) - 2 and float(o["sun_min"]) >= 6:
            n += 1
    return n


def metrics(placements, df, floor_area_sqft, load_limit_kg_m2=150.0, north_vec=None):
    n = len(placements)
    weights = [float(df.loc[p["plant_id"], "weight_kg"]) for p in placements]
    total_w = sum(weights)
    area_m2 = floor_area_sqft * 0.092903
    avg = total_w / area_m2 if area_m2 else 0
    peak = (max(weights) / P.CELL_AREA_M2) if weights else 0
    effort = sum(EFFORT_H[df.loc[p["plant_id"], "maint"]] for p in placements)
    plants = sum(int(df.loc[p["plant_id"], "per_cell"]) for p in placements)
    warns = []
    if avg > load_limit_kg_m2:
        warns.append(f"Average added load {avg:.0f} kg/m² is above your limit of {load_limit_kg_m2:.0f} kg/m².")
    if peak > 2 * load_limit_kg_m2:
        warns.append(f"Heaviest planters press {peak:.0f} kg/m² locally. Ask a structural engineer.")
    advice = []
    windy = sum(1 for p in placements if df.loc[p["plant_id"], "wind_risk"] == "high"
                and (float(df.loc[p["plant_id"], "height_ft"]) >= 4 or p["form"] == "climber"))
    if windy:
        advice.append(f"{windy} tall/climbing planter(s) need stakes or wall anchors before the Mar-May nor'wester season.")
    if any(p["form"] == "shrub" and float(df.loc[p["plant_id"], "weight_kg"]) > 150 for p in placements):
        advice.append("Large shrub/tree pots are heavy: place them over beams/columns after an engineer's check.")
    if north_vec is not None:
        sc = shade_conflicts(placements, df, north_vec)
        if sc:
            advice.append(f"{sc} sun-loving plant(s) sit in the shadow of a taller plant. Press Reshuffle or move them.")
    advice.append("Do not leave standing water in drain trays (dengue mosquitoes breed in it). Empty weekly.")
    return {"advice": advice, "planters": n, "plants": plants, "weight_kg": round(total_w), "avg_load": round(avg),
            "peak_load": round(peak), "effort_h_week": round(effort, 1), "warnings": warns,
            "species": len({p["plant_id"] for p in placements})}


def build_bom(placements, df, mats, labour_pct=15.0):
    rows = []
    per = {}
    for p in placements:
        per[p["plant_id"]] = per.get(p["plant_id"], 0) + 1
    for pid, cnt in sorted(per.items(), key=lambda kv: -kv[1]):
        r = df.loc[pid]
        q = cnt * int(r["per_cell"])
        rows.append((f"Plant: {r['name_en']}", q, "pcs", float(r["cost_bdt"]), q * float(r["cost_bdt"])))
    n = len(placements)
    litres = sum(float(df.loc[p["plant_id"], "soil_litres"]) for p in placements)
    support = sum(1 for p in placements if df.loc[p["plant_id"], "support"])
    shade_sqft = sum(4 for p in placements if p["zone"] == "AFTERNOON_SUN") * 1.3

    def add(name, qty, item):
        if qty > 0 and item in mats.index:
            c = float(mats.loc[item, "unit_cost_bdt"])
            rows.append((name, round(qty, 1), mats.loc[item, "unit"], c, round(qty * c, 0)))

    add("Planter box 2×2 ft", n, "planter_box_2x2ft")
    add("Carrying materials up the outer stair (per planter)", sum(1 for p in placements if p.get("level", 1) == 2),
        "stair_carry_labour")
    add("Light soil mix", litres, "soil_mix_light")
    add("Drip kit", n, "drip_kit_per_planter")
    add("Drain tray", n, "drain_tray_per_planter")
    add("Trellis frame", support, "trellis_frame")
    add("Railing hook brackets (hanging plants)", sum(1 for p in placements if p["form"] == "hanging"), "railing_hook_bracket")
    add("Wall anchor set (climbers)", sum(1 for p in placements if p["form"] == "climber"), "wall_anchor_set")
    add("Wind stake kit (tall, wind-exposed)", sum(1 for p in placements if p["form"] in ("shrub", "bush")
        and df.loc[p["plant_id"], "wind_risk"] == "high" and float(df.loc[p["plant_id"], "height_ft"]) >= 4), "wind_stake_kit")
    add("Shade net (afternoon zones)", shade_sqft, "shade_net_50pct")
    add("Waterproofing / leak check", n * 4, "waterproof_leak_check")
    sub = sum(r[4] for r in rows)
    rows.append((f"Installation labour ({labour_pct:.0f}%)", 1, "lot", round(sub * labour_pct / 100), round(sub * labour_pct / 100)))
    total = sum(r[4] for r in rows)
    out = pd.DataFrame(rows, columns=["Item", "Qty", "Unit", "Unit cost (BDT)", "Cost (BDT)"])
    return out, float(total)


def ai_prompt(placements, cells_desc, bearing_text, grid_ft=2):
    counts = {}
    for p in placements:
        counts.setdefault(p["name"], []).append(f"(row {p['row'] + 1}, col {p['col'] + 1})")
    lines = [f"- {name}: {len(v)} planter(s) at " + ", ".join(v[:8]) + (" ..." if len(v) > 8 else "")
             for name, v in counts.items()]
    return ("Create a realistic photograph of a rooftop garden. Keep the roof shape, walls and railings exactly as in "
            "the attached image. The floor is divided into a grid of " + f"{grid_ft} ft squares " + "(rows from the top, "
            "columns from the left). Place 2×2 ft planters with these plants and no others:\n" + "\n".join(lines) +
            f"\nLeave all other cells clear for walking. {bearing_text}. Natural daylight. "
            "Do not add furniture or text. This is an illustrative impression only.")


# ------------------------------------------------------------------ two-level roof
def level_name(roof, lv):
    fl = roof.get("floors", [5, 6])
    return f"{fl[lv - 1]}th floor" if lv - 1 < len(fl) else f"Level {lv}"


def generate_roof(roof, cells, df, prefs, month, variant, north_vec, taps=None, seed=0, grid_ft=2.0):
    """Generate a layout for every reachable level. Landings/stair entries are kept clear.
    The upper level is skipped (with a note) when no outer stair is marked."""
    eff = RM.effective_cells(roof, cells, grid_ft)
    rows, cols = RM.grid_dims(roof, grid_ft)
    lc = RM.level_cells(roof, grid_ft)
    taps = taps or {}
    placements, notes = [], []
    for lv in (1, 2):
        if not lc[lv]:
            continue
        if lv == 2 and not RM.has_outer_stair(roof):
            notes.append(f"{level_name(roof, 2)} skipped: no outer stair is marked, so it cannot be reached.")
            continue
        sub = {k: v for k, v in eff.items() if RM.parse_key(k) in lc[lv]}
        res = generate(sub, cols, rows, df, prefs, month, variant, north_vec, tap=taps.get(lv),
                       seed=seed + (0 if lv == 1 else 1000), domain=lc[lv],
                       edge=RM.railing_cells(roof, lv, grid_ft))
        for p in res["placements"]:
            p["level"] = lv
            placements.append(p)
        pre = f"{level_name(roof, lv)}: " if lc[2] else ""
        notes += [pre + n for n in res["notes"]]
    return {"placements": placements, "notes": notes, "variant": variant}


def metrics_roof(placements, df, roof, limit, north_vec, l2_factor=0.6, grid_ft=2.0):
    """Per-level load/effort checks combined into one dict (same keys as metrics())."""
    A = RM.areas(roof)
    parts = {}
    for lv in (1, 2):
        if lv == 2 and A[2] <= 0:
            continue
        pl = [p for p in placements if p.get("level", 1) == lv]
        parts[lv] = metrics(pl, df, A[lv], limit * (l2_factor if lv == 2 else 1.0), north_vec)
    two = 2 in parts
    out = {"planters": sum(m["planters"] for m in parts.values()), "plants": sum(m["plants"] for m in parts.values()),
           "weight_kg": sum(m["weight_kg"] for m in parts.values()),
           "avg_load": max(m["avg_load"] for m in parts.values()), "peak_load": max(m["peak_load"] for m in parts.values()),
           "effort_h_week": round(sum(m["effort_h_week"] for m in parts.values()), 1),
           "species": len({p["plant_id"] for p in placements}), "warnings": [], "advice": [], "levels": parts}
    for lv, m in parts.items():
        pre = f"{level_name(roof, lv)}: " if two else ""
        out["warnings"] += [pre + w for w in m["warnings"]]
        for a in m["advice"]:
            if a not in out["advice"]:
                out["advice"].append(pre + a if "standing water" not in a else a)
    if two and parts[2]["planters"]:
        out["advice"].append(f"{level_name(roof, 2)}: everything is carried up the small outer stair, so use light "
                             "planters and soil mix, and carry in small loads.")
        out["advice"].append(f"{level_name(roof, 2)} sits over the stair-house slab: the load limit used is "
                             f"{int(l2_factor * 100)}% of the main roof. A structural engineer must confirm it.")
    return out
