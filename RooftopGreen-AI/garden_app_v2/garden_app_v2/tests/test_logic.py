import math, plants as P, layout as L, roofcore as rc

def test_north_arrow():
    assert rc.north_angle_deg(180) == 0          # Side 1 faces south -> north is up
    assert rc.north_angle_deg(0) == 180
    nx, ny = rc.north_vector(180); assert abs(nx) < 1e-9 and ny < 0
    nx, ny = rc.north_vector(90);  assert nx > 0 and abs(ny) < 1e-9   # Side 1 faces east (down on screen) -> north points right

def test_plant_db_valid():
    df = P.load_plants(); assert len(df) >= 40 and not df["verified"].any()

def test_zone_rules():
    df = P.load_plants()
    prefs = {"mix": {"vegetable": 50, "flower": 50}, "effort": "weekends", "harvest": "home", "kids_pets": False}
    assert len(P.candidates_for_zone(df, "SHADE", 11, prefs)) > 0
    summer = P.candidates_for_zone(df, "AFTERNOON_SUN", 5, prefs)
    low_heat = set(df[df.heat == "low"].id)
    assert not (set(summer["id"]) & low_heat)       # low heat tolerance excluded in summer
    kids = P.candidates_for_zone(df, "FULL_SUN", 11, {**prefs, "kids_pets": True})
    assert not (set(kids["id"]) & set(df[df.hazard != ""].id))

def test_layout_rules():
    df = P.load_plants()
    prefs = {"mix": {"vegetable": 40, "flower": 30, "fruit": 15, "herb": 15}, "effort": "weekends",
             "harvest": "home", "kids_pets": False}
    cells = {f"{r},{c}": "FULL_SUN" for r in range(8) for c in range(10)}
    cells["3,9"] = "BLOCKED"; cells["7,0"] = "WALKWAY"
    for v in L.VARIANTS:
        a = L.generate(cells, 10, 8, df, prefs, 11, v, rc.north_vector(180), seed=3)
        b = L.generate(cells, 10, 8, df, prefs, 11, v, rc.north_vector(180), seed=3)
        assert a["placements"] == b["placements"]                       # deterministic
        cs = {(p["row"], p["col"]) for p in a["placements"]}
        assert (3, 9) not in cs and (7, 0) not in cs
        assert not L._unreachable(cs, 8, 10, {(3, 9)})                  # every planter reachable


def test_forms_and_wall_rules():
    import collections
    df = P.load_plants()
    assert set(df.form) == set(P.FORMS)
    assert (df[df.form.isin(P.WALL_FORMS)].needs_wall).all()
    prefs = {"mix": {"vegetable": 30, "flower": 40, "fruit": 10, "herb": 10, "ornamental": 10}, "effort": "weekends",
             "harvest": "home", "kids_pets": False}
    cells = {f"{r},{c}": "FULL_SUN" for r in range(8) for c in range(10)}
    edge = L.edge_cells(8, 10)
    for month in (3, 7, 12):
        for v in L.VARIANTS:
            res = L.generate(cells, 10, 8, df, prefs, month, v, rc.north_vector(180), seed=5)
            for p in res["placements"]:
                if df.loc[p["plant_id"], "needs_wall"]:
                    assert (p["row"], p["col"]) in edge          # climbers/hangers only on railing cells


def test_monsoon_and_bloom_rules():
    df = P.load_plants()
    prefs = {"mix": {"flower": 100}, "effort": "weekends", "harvest": "decor", "kids_pets": False}
    july = set(P.candidates_for_zone(df, "FULL_SUN", 7, prefs)["id"])
    assert not (july & set(df[~df.monsoon_ok].id))
    assert P.in_bloom(df.loc["marigold"], 12) and not P.in_bloom(df.loc["marigold"], 6)
    assert P.months_active("none") == set()


def test_sprites_only_when_approved(tmp_path):
    import cv2, numpy as np, sprites as SP
    base = str(tmp_path)
    png = str(tmp_path / "x.png")
    cv2.imwrite(png, np.dstack([np.full((40, 30, 3), 120, np.uint8), np.full((40, 30), 255, np.uint8)]))
    assert SP.load_sprite("tomato", "mature", base) is None
    SP.approve("tomato", "mature", png, "tester", base=base)
    assert SP.load_sprite("tomato", "mature", base) is not None
    assert SP.load_sprite("tomato", "mid", base) is None            # other stage not approved
    SP.reject("tomato", "mature", base=base)
    assert SP.load_sprite("tomato", "mature", base) is None


def test_3d_counts_and_sprite_paste(tmp_path):
    import cv2, numpy as np, plan_render as pr, sprites as SP
    df = P.load_plants()
    info = {"floor_x0": 0, "floor_y0": 0, "floor_w": 800, "floor_h": 600, "ppf": 40, "image_w": 800, "image_h": 600}
    floor = np.full((600, 800, 3), 120, np.uint8)
    strips = [np.full((120, w, 3), 90, np.uint8) for w in (800, 600, 800, 600)]
    pl = [{"row": 1, "col": 1, "plant_id": "tomato", "name": "Tomato", "category": "vegetable", "form": "bush", "zone": "FULL_SUN"},
          {"row": 2, "col": 3, "plant_id": "lemon", "name": "Lemon", "category": "fruit", "form": "shrub", "zone": "FULL_SUN"}]
    for st in pr.STAGE_K:
        out = pr.render_pseudo3d(floor, strips, pl, df, info, 2, 3, stage=st, month=12)
        assert out.shape == (780, 1200, 3)
    base = str(tmp_path)
    png = str(tmp_path / "s.png")
    cv2.imwrite(png, np.dstack([np.full((60, 40, 3), (0, 0, 255), np.uint8), np.full((60, 40), 255, np.uint8)]))
    SP.approve("tomato", "mature", png, "tester", base=base)
    out2 = pr.render_pseudo3d(floor, strips, pl, df, info, 2, 3, stage="mature", month=12, sprites_base=base)
    assert (out2[..., 2] > 200).any()                                # red sprite pixels were pasted


def test_cutout():
    import numpy as np, importlib.util, os
    spec = importlib.util.spec_from_file_location("ms", os.path.join(os.path.dirname(__file__), "..", "tools", "make_sprites.py"))
    ms = importlib.util.module_from_spec(spec); spec.loader.exec_module(ms)
    img = np.full((100, 100, 3), 255, np.uint8); img[30:80, 40:70] = (30, 120, 30)
    out = ms.cutout(img)
    assert out.shape[2] == 4 and out.shape[0] <= 60 and out[..., 3].max() == 255
