"""Sun position and the shadow that the higher block casts on the lower roof. No Streamlit.
Simplifications (state them in the UI): only the block's shadow is computed (not neighbouring buildings,
trees or parapets); times are local SOLAR time; mid-month day; flat roofs."""
import math
import roofmodel as RM
import roofcore as rc

CUM_DAYS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
MAX_SHADOW_FT = 80.0
HOURS = tuple(range(7, 18))                     # 07:00 - 17:00 solar time


def declination_deg(month, day=15):
    n = CUM_DAYS[month - 1] + day
    return 23.45 * math.sin(math.radians(360.0 / 365.0 * (284 + n)))


def solar_position(lat, month, hour, day=15):
    """(altitude_deg, azimuth_deg from north clockwise) at local solar time `hour`."""
    dec, phi, H = math.radians(declination_deg(month, day)), math.radians(lat), math.radians(15.0 * (hour - 12))
    sin_alt = math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(H)
    alt = math.asin(max(-1.0, min(1.0, sin_alt)))
    az = math.atan2(math.sin(H), math.cos(H) * math.sin(phi) - math.tan(dec) * math.cos(phi)) + math.pi
    return math.degrees(alt), math.degrees(az) % 360.0


def north_plan(bearing):
    """North as a unit vector in plan coordinates (x right, y up) when Side 1 faces `bearing`."""
    nx, ny_img = rc.north_vector(bearing)
    return (nx, -ny_img)


def sun_dir_plan(az_deg, bearing):
    """Horizontal unit vector pointing TOWARDS the sun, in plan coordinates."""
    n = north_plan(bearing)
    e = (n[1], -n[0])                                       # east is 90 degrees clockwise from north
    a = math.radians(az_deg)
    return (math.sin(a) * e[0] + math.cos(a) * n[0], math.sin(a) * e[1] + math.cos(a) * n[1])


def shadow_vector(height_ft, alt_deg, az_deg, bearing):
    """Where the top of a wall `height_ft` high throws its shadow, relative to its foot (plan feet)."""
    if alt_deg <= 1.0:
        return None
    length = min(height_ft / math.tan(math.radians(alt_deg)), MAX_SHADOW_FT)
    d = sun_dir_plan(az_deg, bearing)
    return (-d[0] * length, -d[1] * length)


def point_shaded(q, rect, s):
    """Is plan point q inside rect swept along s (the block's shadow)?"""
    x0, y0, x1, y1 = rect
    n = max(2, int(math.hypot(*s) / 0.5) + 2)
    for i in range(n + 1):
        u = i / n
        x, y = q[0] - u * s[0], q[1] - u * s[1]
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True
    return False


def hourly_shade(roof, lat, month, bearing, grid_ft=2.0, hours=HOURS):
    """{ "r,c": {hour: sunlit(bool)} } for level-1 cells; only hours with the sun above 8 degrees."""
    br = RM.block_rect(roof)
    lc = RM.level_cells(roof, grid_ft)
    out = {}
    for hr in hours:
        alt, az = solar_position(lat, month, hr)
        if alt <= 8.0:
            continue
        s = shadow_vector(roof["diff_ft"], alt, az, bearing) if br else None
        for rcell in lc[1]:
            q = RM.cell_center(roof, rcell[0], rcell[1], grid_ft)
            shaded = bool(br and s and point_shaded(q, br, s))
            out.setdefault(RM.key(rcell), {})[hr] = not shaded
    return out


def classify(hours_sunlit):
    """FULL_SUN / MORNING_SUN / AFTERNOON_SUN / SHADE from {hour: sunlit}."""
    hs = sorted(hours_sunlit)
    if not hs:
        return "SHADE"
    am = [h for h in hs if h < 12]
    pm = [h for h in hs if h >= 12]
    f_all = sum(hours_sunlit[h] for h in hs) / len(hs)
    f_am = (sum(hours_sunlit[h] for h in am) / len(am)) if am else 0.0
    f_pm = (sum(hours_sunlit[h] for h in pm) / len(pm)) if pm else 0.0
    if f_all >= 0.75:
        return "FULL_SUN"
    if f_all <= 0.30:
        return "SHADE"
    return "MORNING_SUN" if f_am >= f_pm else "AFTERNOON_SUN"


def suggest_types(roof, lat, month, bearing, grid_ft=2.0):
    """{ "r,c": TYPE } suggestions for every cell. Upper roof = FULL_SUN (nothing higher nearby is modelled);
    lower roof follows the block's shadow."""
    lc = RM.level_cells(roof, grid_ft)
    shade = hourly_shade(roof, lat, month, bearing, grid_ft)
    out = {RM.key(c): "FULL_SUN" for c in lc[2]}
    for k, hrs in shade.items():
        out[k] = classify(hrs)
    for c in lc[1]:
        out.setdefault(RM.key(c), "FULL_SUN")
    return out
