"""Interactive 3D impression of the two-level roof (three.js, bundled locally)."""
import os
import numpy as np
import streamlit.components.v1 as components
import roofmodel as RM
from painter_component import data_url

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "components", "viewer3d")
_component = components.declare_component("garden_viewer3d", path=_PATH)

STAGE_K = {"seedling": 0.35, "growing": 0.65, "mature": 1.0}


def _hex_rgb(h, default=(70, 140, 70)):
    try:
        h = h.lstrip("#"); return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    except Exception:
        return list(default)


def build_scene(roof, placements, df, lat, month, bearing, north_vec, grid_ft=2.0,
                strips=None, floor_bgr=None, stage="mature", rail_ft=3.0, hour=10.0):
    """Plain-JSON description of the scene. strips = 4 BGR images (side 1..4) or None."""
    W, D = float(roof["W"]), float(roof["D"])
    corners = [(0, 0), (W, 0), (W, D), (0, D)]
    side_pts = {str(i + 1): [list(corners[i]), list(corners[(i + 1) % 4])] for i in range(4)}
    br = RM.block_rect(roof) if roof.get("block") else None
    faces = [{"p0": list(f["p0"]), "p1": list(f["p1"]), "normal": list(f["normal"])} for f in RM.step_faces(roof)]
    ops = []
    for op in roof.get("openings", []):
        g = RM.opening_geometry(roof, op)
        ops.append({"kind": g["kind"], "centre": list(g["centre"]), "normal": list(g["normal"]), "width": g["width"]})
    plants = []
    for p in placements:
        r, c = p["row"], p["col"]
        cx, cy = RM.cell_center(roof, r, c, grid_ft)
        row = df.loc[p["plant_id"]]
        plants.append({"x": cx, "y": cy, "level": p.get("level", 1), "form": row["form"], "category": row["category"],
                       "height": float(row["height_ft"]), "canopy": float(row["canopy_ft"]),
                       "color": [70, 140, 70], "bloom": _hex_rgb(str(row.get("bloom_hex", "#e91e63"))),
                       "flowering": str(row.get("bloom_months", "none")) != "none",
                       "support": bool(row["support"]), "sprite": None})
    sc = {"W": W, "D": D, "diff": float(roof.get("diff_ft", 10)), "rail": rail_ft,
          "poly1": [list(q) for q in RM.level_polygon(roof, 1)], "block": list(br) if br else None,
          "side_pts": side_pts, "segments": RM.outer_side_segments(roof), "faces": faces, "openings": ops,
          "stair_steps": RM.STAIR_RISE_STEPS, "stair_run": RM.LANDING_FT["outer_stair"],
          "plants": plants, "stage_k": STAGE_K.get(stage, 1.0), "lat": lat, "month": month, "hour": hour,
          "north": [float(north_vec[0]), float(north_vec[1])],
          "names": [f"{roof['floors'][0]}th floor roof", f"{roof['floors'][1]}th floor roof"],
          "strips": [data_url(s, 80) if s is not None else None for s in (strips or [None] * 4)],
          "floor_tex": data_url(floor_bgr, 85) if floor_bgr is not None else None,
          "title": "3D impression",
          "legend": ["Brown boxes = planters", "Grey blocks = outer stair", "Plain concrete step wall"]}
    return sc


def viewer3d(scene, scene_id, height=560, key="viewer3d"):
    return _component(scene=scene, scene_id=scene_id, height=height, key=key, default=None)
