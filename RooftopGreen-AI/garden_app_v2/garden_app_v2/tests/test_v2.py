import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import roofmodel as RM, paint as PT, sunlight as SUN, layout as LY, plants as PL, roofcore as rc, demo as DM

def roof(corner="C"):
    return RM.new_roof(20, 16, {"w": 8, "d": 8, "corner": corner}, 10, openings=DM.DEMO_ROOF["openings"])

def test_areas_all_corners():
    for c in "ABCD":
        A = RM.areas(roof(c)); assert A[1] == 256 and A[2] == 64 or A[1] + A[2] == 320

def test_levels_partition_grid():
    r = roof(); lc = RM.level_cells(r); rows, cols = RM.grid_dims(r)
    assert len(lc[1]) + len(lc[2]) == rows * cols and not (lc[1] & lc[2])

def test_opening_cells_forced_walkway():
    r = roof(); eff = RM.effective_cells(r, {}); assert set(eff.values()) == {"WALKWAY"} and len(eff) >= 6

def test_validate():
    assert RM.validate(RM.new_roof(10, 10, {"w": 20, "d": 4, "corner": "A"}))

def test_paint_brush_and_rect():
    info = {"floor_x0": 120, "floor_y0": 120, "floor_w": 800, "floor_h": 640, "ppf": 40, "image_w": 1040, "image_h": 880}
    sel = PT.select({"tool": "rect", "points": [[121, 121], [279, 279]]}, info, 2.0)
    assert len(sel) == 4
    new, n = PT.apply_selection({}, sel, "SHADE"); assert n == 4 and set(new.values()) == {"SHADE"}
    new2, n2 = PT.apply_selection(new, sel, None); assert n2 == 4 and not new2

def test_sun_shadow_west_of_block_afternoon():
    s = SUN.suggest_types(roof(), 25.75, 12, 180.0)
    assert "AFTERNOON_SUN" in set(s.values()) or "SHADE" in set(s.values())
    lc = RM.level_cells(roof())
    assert all(s[RM.key(c)] == "FULL_SUN" for c in lc[2])

def test_layout_per_level_and_landings():
    r = roof(); df = PL.load_plants()
    cells = {RM.key(c): "FULL_SUN" for lv in RM.level_cells(r).values() for c in lv}
    res = LY.generate_roof(r, cells, df, {"mix": {"vegetable": 40, "flower": 30, "fruit": 15, "herb": 15, "ornamental": 0},
                                          "effort": "weekends", "harvest": "home", "kids_pets": False}, 11, "Balanced",
                           rc.north_vector(180.0))
    levels = {p["level"] for p in res["placements"]}
    assert levels == {1, 2}
    land = set(RM.opening_cells(r))
    assert not any(RM.key((p["row"], p["col"])) in land for p in res["placements"])

def test_no_stair_means_no_upper_plants():
    r = RM.new_roof(20, 16, {"w": 8, "d": 8, "corner": "C"}, 10, openings=[])
    df = PL.load_plants()
    cells = {RM.key(c): "FULL_SUN" for lv in RM.level_cells(r).values() for c in lv}
    res = LY.generate_roof(r, cells, df, {"mix": {"vegetable": 100, "flower": 0, "fruit": 0, "herb": 0, "ornamental": 0},
                                          "effort": "daily", "harvest": "home", "kids_pets": False}, 11, "Balanced",
                           rc.north_vector(180.0))
    assert {p["level"] for p in res["placements"]} == {1}

def test_app_demo_flow_and_marker():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py"), default_timeout=120).run()
    [b for b in at.sidebar.button if "demo" in b.label][0].click().run()
    assert not at.exception and len(at.session_state.cells) == 80
    before = dict(at.session_state.cells)
    at.radio(key="brush").set_value("🟪 Shade (little or no sun)").run()
    at.session_state["_test_paint"] = {"nonce": 1, "tool": "rect", "points": [[121, 121], [279, 279]], "radius_ft": 2}
    at.run(); assert not at.exception
    assert at.session_state.cells != before and list(at.session_state.cells.values()).count('SHADE') == 4
    for step in ("9 · Garden options",):
        at.session_state.step = step; at.run()
    [b for b in at.button if "Generate 3" in b.label][0].click().run()
    assert not at.exception and at.session_state.options
    at.session_state.chosen = "Balanced"; at.session_state.step = "10 · Final plan"; at.run()
    assert not at.exception
