"""Plant database loading, season/zone rules, and candidate ranking. No Streamlit."""
import os
import pandas as pd

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December"]
CATEGORIES = ["vegetable", "flower", "fruit", "herb", "ornamental"]
FORMS = ["patch", "bush", "climber", "hanging", "shrub", "succulent"]
WALL_FORMS = ("climber", "hanging")
FORMS = ["patch", "bush", "climber", "hanging", "shrub", "succulent"]
FORM_LABEL = {"patch": "Patch (low, dense)", "bush": "Bush", "climber": "Climber (needs wall + trellis)",
              "hanging": "Hanging / trailing (railing)", "shrub": "Shrub / small tree (large pot)",
              "succulent": "Succulent / foliage"}
PLANT_ZONES = ["FULL_SUN", "MORNING_SUN", "AFTERNOON_SUN", "SHADE"]
ZONE_HOURS = {"FULL_SUN": 8.0, "MORNING_SUN": 5.0, "AFTERNOON_SUN": 5.0, "SHADE": 2.0}
ZONE_LABEL = {"FULL_SUN": "Full Sun", "MORNING_SUN": "Morning Sun",
              "AFTERNOON_SUN": "Afternoon Sun", "SHADE": "Shade"}
MAINT_SCORE = {"low": 1.0, "med": 0.5, "high": 0.0}
REQUIRED = ["id", "name_en", "category", "form", "canopy_ft", "needs_wall", "bloom_months", "wind_risk", "monsoon_ok", "form", "canopy_ft", "needs_wall", "bloom_months", "wind_risk", "monsoon_ok", "sun_min", "sun_max", "water", "soil_depth_in", "per_cell",
            "height_ft", "support", "months", "heat", "days", "maint", "cost_bdt", "verified"]
CELL_AREA_M2 = (2 * 0.3048) ** 2        # one 2 ft x 2 ft cell


def _bool(s):
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y"])


def months_active(text):
    t = str(text).strip().lower()
    if t in ("all", "", "nan"):
        return set(range(1, 13))
    if t == "none":
        return set()
    a, b = t.split("-")
    i, j = MONTHS.index(a[:3]) + 1, MONTHS.index(b[:3]) + 1
    return set(range(i, j + 1)) if i <= j else set(range(i, 13)) | set(range(1, j + 1))


def load_plants(path=None):
    df = pd.read_csv(path or os.path.join(DATA, "plants.csv"))
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        raise ValueError(f"plants.csv is missing columns: {miss}")
    bad = []
    for i, r in df.iterrows():
        try:
            ok = (r.category in CATEGORIES and r.form in FORMS and r.wind_risk in ("low", "med", "high") and float(r.canopy_ft) > 0 and r.form in FORMS and r.wind_risk in ("low", "med", "high") and
                  float(r.canopy_ft) > 0 and r.water in ("low", "med", "high") and
                  r.heat in ("low", "med", "high") and r.maint in ("low", "med", "high") and
                  float(r.sun_min) <= float(r.sun_max) and float(r.soil_depth_in) > 0 and
                  int(r.per_cell) >= 1 and float(r.cost_bdt) >= 0)
            months_active(r.months)
            months_active(r.bloom_months)
            months_active(r.bloom_months) if str(r.bloom_months).strip().lower() != "none" else None
        except Exception:
            ok = False
        if not ok:
            bad.append(f"row {i + 2} ({r.get('id', '?')})")
    if bad:
        raise ValueError("Invalid plant rows: " + ", ".join(bad))
    df = df.copy()
    df["support"] = _bool(df["support"])
    df["needs_wall"] = _bool(df["needs_wall"])
    df["monsoon_ok"] = _bool(df["monsoon_ok"])
    df["verified"] = _bool(df["verified"])
    df["needs_wall"] = _bool(df["needs_wall"])
    df["monsoon_ok"] = _bool(df["monsoon_ok"])
    df["hazard"] = df.get("hazard", "").fillna("") if "hazard" in df.columns else ""
    df["name_bn"] = df["name_bn"].fillna("") if "name_bn" in df.columns else ""
    df["bloom_hex"] = df["bloom_hex"].fillna("#66bb6a") if "bloom_hex" in df.columns else "#66bb6a"
    litres = CELL_AREA_M2 * df["soil_depth_in"].astype(float) * 0.0254 * 1000
    df["soil_litres"] = litres.round(0)
    df["weight_kg"] = (litres * 0.8 + 6).round(0)          # wet lightweight mix + box
    return df.set_index("id", drop=False)


def load_materials(path=None):
    return pd.read_csv(path or os.path.join(DATA, "materials.csv")).set_index("item")


def in_bloom(row, month):
    """True when the plant is flowering/fruiting in `month` (bloom_months 'none' = foliage only)."""
    b = str(row["bloom_months"]).strip().lower()
    return False if b == "none" else month in months_active(b)


def season_ok(row, month):
    return month in months_active(row["months"])


def in_bloom(row, month):
    return month in months_active(row["bloom_months"])


def fits_zone(row, zone, month):
    h = ZONE_HOURS[zone]
    if h < float(row["sun_min"]) - 0.5:
        return False, "needs more sun than this zone gives"
    if h > float(row["sun_max"]) + 0.5:
        return False, "too much sun for this plant"
    if zone == "AFTERNOON_SUN" and row["heat"] == "low" and 3 <= month <= 10:
        return False, "low heat tolerance (hot afternoon sun Mar-Oct)"
    return True, ""


def normalized_mix(prefs, bias=None):
    mix = {c: float(prefs.get("mix", {}).get(c, 0)) * (bias or {}).get(c, 1.0) for c in CATEGORIES}
    tot = sum(mix.values())
    if tot <= 0:
        mix = {c: 1.0 for c in CATEGORIES}
        tot = float(len(CATEGORIES))
    return {c: v / tot for c, v in mix.items()}


def candidates_for_zone(df, zone, month, prefs, bias=None, maint_extra=0.0):
    """Ranked DataFrame of plants that fit the zone and season, with plain-language reasons."""
    mix = normalized_mix(prefs, bias)
    effort = prefs.get("effort", "weekends")
    maint_w = {"daily": 0.3, "weekends": 0.9, "managed": 0.2}.get(effort, 0.5) + maint_extra
    harvest = prefs.get("harvest", "home")
    rows = []
    for _, r in df.iterrows():
        if prefs.get("kids_pets") and r["hazard"]:
            continue
        if not prefs.get("allow_wall", True) and r["needs_wall"]:
            continue
        if not prefs.get("allow_trees", True) and r["form"] == "shrub":
            continue
        if 6 <= month <= 9 and not r["monsoon_ok"]:
            continue                                  # does not like monsoon rain
        if not season_ok(r, month):
            continue
        if not r["monsoon_ok"] and 6 <= month <= 9:
            continue                      # dislikes heavy monsoon rain
        ok, _ = fits_zone(r, zone, month)
        if not ok:
            continue
        reasons = [f"fits {ZONE_LABEL[zone]}", f"in season in {MONTH_NAMES[month - 1]}"]
        if r["needs_wall"]:
            reasons.append("grows on the railing/wall edge" + (" with a trellis" if r["support"] else ""))
        s = 2.0 * mix[r["category"]]
        if mix[r["category"]] >= 0.15:
            reasons.append(f"matches your {r['category']} preference ({mix[r['category']]:.0%})")
        center = (float(r["sun_min"]) + float(r["sun_max"])) / 2
        fit = max(0.0, 1 - abs(ZONE_HOURS[zone] - center) / 6)
        s += 1.5 * fit
        s += maint_w * MAINT_SCORE[r["maint"]]
        if r["maint"] == "low":
            reasons.append("low maintenance")
        if harvest in ("home", "sell") and r["category"] in ("vegetable", "fruit", "herb"):
            s += 0.5
            reasons.append("gives a harvest")
        if harvest == "decor" and r["category"] in ("flower", "ornamental"):
            s += 0.5
            reasons.append("decorative")
        if r["category"] == "vegetable" and 0 < float(r["days"]) <= 60:
            s += 0.2
            reasons.append(f"quick crop (~{int(r['days'])} days)")
        rows.append({"id": r["id"], "Plant": r["name_en"], "Bangla": r["name_bn"], "Category": r["category"],
                     "Form": r["form"], "Score": round(s, 2), "Why": "; ".join(reasons),
                     "Verified": "✅" if r["verified"] else "⚠️ unverified"})
    out = pd.DataFrame(rows)
    return out.sort_values("Score", ascending=False).reset_index(drop=True) if len(out) else out
