import datetime
import json
import math

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates as img_click

import layout as L
import plan_render as pr
import plants as P
import sprites as SP
import roofcore as rc
import roofmodel as RM
import paint as PT
import sunlight as SUN
import plan_overlays as PO
import demo as DEMO
from painter_component import painter, data_url
from viewer3d_component import viewer3d, build_scene

st.set_page_config(page_title="Rooftop Garden Planner", page_icon="🌿", layout="wide")

PPF = 40
GRID_FT = 2
STEPS = ["1 · Roof & site", "2 · Upload photos", "3 · Mark railings", "4 · Floor sample",
         "5 · Realistic image", "6 · Grid & types", "7 · Preferences", "8 · Candidate plants",
         "9 · Garden options", "10 · Final plan"]
CORNER_HELP = ["1 · top-left", "2 · top-right", "3 · bottom-right (railing meets floor)",
               "4 · bottom-left (railing meets floor)"]
dialog = getattr(st, "dialog", None) or getattr(st, "experimental_dialog")


@st.cache_data
def get_plants():
    return P.load_plants()


@st.cache_data
def get_materials():
    return P.load_materials()


# ================================================================= state
def init_state():
    S = st.session_state
    S.setdefault("step", STEPS[0])
    S.setdefault("cfg", {"L": [20.0, 15.0, 20.0, 15.0], "use_diag": False, "diag": 25.0, "height": 3.0})
    S.setdefault("site", {"city": "Rangpur", "lat": 25.75, "lon": 89.25, "bearing": 180.0})
    S.setdefault("imgs", [None] * 4)
    S.setdefault("quads", {i: [] for i in range(4)})
    S.setdefault("mirror", [False] * 4)
    S.setdefault("side", 0)
    S.setdefault("floor_src", 0)
    S.setdefault("floor_pts", [])
    S.setdefault("floor_sample", None)
    S.setdefault("realistic", None)
    S.setdefault("info", None)
    S.setdefault("ai_img", None)
    S.setdefault("cells", {})
    S.setdefault("undo", [])
    S.setdefault("anchor", None)
    S.setdefault("tap", None)
    S.setdefault("fl", {"seed": 7, "joint": 10.0, "tex": 4.0, "base": "#787670"})
    S.setdefault("prefs", {"mix": {"vegetable": 40, "flower": 30, "fruit": 15, "herb": 15, "ornamental": 0},
                           "effort": "weekends", "budget": 50000, "style": "Modern", "harvest": "home",
                           "kids_pets": False, "month": datetime.date.today().month,
                           "load_limit": 150.0, "labour": 15.0})
    S.setdefault("seed", 1)
    S.setdefault("roof", {"block": None, "diff_ft": 10.0, "floors": [5, 6], "openings": []})
    S.setdefault("redo", [])
    S.setdefault("paint_msg", "")
    S.setdefault("demo_strips", None)
    S.setdefault("options", {})
    S.setdefault("opt_sig", None)
    S.setdefault("chosen", None)


def roof_now():
    """RoofModel for the current inputs (W, D from the side lengths)."""
    S = st.session_state
    L_ = S.cfg["L"]
    r = S.roof
    return RM.new_roof((L_[0] + L_[2]) / 2, (L_[1] + L_[3]) / 2, r.get("block"), r.get("diff_ft", 10.0),
                       tuple(r.get("floors", [5, 6])), r.get("openings", []))


def two_level():
    return bool(st.session_state.roof.get("block"))


def strips_any():
    """Photo strips if available, else the demo's synthetic strips, else None."""
    S = st.session_state
    if strips_ready():
        return build_strips()
    return S.demo_strips


def show_overlay(img):
    return PO.overlay_roof(img, st.session_state.info, roof_now(), GRID_FT) if two_level() and st.session_state.info else img


def load_demo():
    S = st.session_state
    S.cfg = {"L": list(DEMO.DEMO_L), "use_diag": False, "diag": 25.0, "height": 3.0}
    S.roof = json.loads(json.dumps(DEMO.DEMO_ROOF))
    S.site = {"city": "Rangpur", "lat": 25.75, "lon": 89.25, "bearing": 180.0}
    for k in list(S.keys()):
        if k in ("H", "UD", "DG", "city", "lat", "lon", "bearing", "L0", "L1", "L2", "L3", "rf_block", "rf_corner",
                 "rf_w", "rf_d", "rf_diff", "rf_f1", "rf_f2", "rf_stair", "rf_sface", "rf_spos", "rf_door",
                 "rf_dface", "rf_dpos") or k.startswith("pf_"):
            S.pop(k, None)
    S.demo_strips = DEMO.demo_strips(S.cfg["L"], PPF, S.cfg["height"])
    S.realistic, S.info = rc.render_realistic(S.demo_strips, S.cfg["L"], PPF)
    S.cells_info = dict(S.info)
    S.ai_img, S.options, S.opt_sig, S.chosen, S.undo, S.redo = None, {}, None, None, [], []
    S.cells = SUN.suggest_types(roof_now(), S.site["lat"], S.prefs["month"], S.site["bearing"], GRID_FT)
    S.tap = (7, 0)
    S.paint_msg = "Demo roof loaded: sunlight types were suggested automatically. Change anything with the marker."
    S.step = STEPS[5]


def goto(step):
    st.session_state.step = step


def fresh_click(key, val):
    if not val:
        return None
    sig = (val.get("unix_time"), val.get("x"), val.get("y"))
    if st.session_state.get("sig_" + key) == sig:
        return None
    st.session_state["sig_" + key] = sig
    return val


def nav(i):
    c1, c2, _ = st.columns([1, 1, 6])
    if i > 0:
        c1.button("◀ Back", on_click=goto, args=(STEPS[i - 1],), key=f"back{i}")
    if i < len(STEPS) - 1:
        c2.button("Next ▶", on_click=goto, args=(STEPS[i + 1],), key=f"next{i}", type="primary")


def strips_ready():
    S = st.session_state
    return all(S.imgs[i] is not None and len(S.quads[i]) == 4 for i in range(4))


def build_strips():
    S = st.session_state
    c = S.cfg
    return [rc.make_strip(S.imgs[i], S.quads[i], c["L"][i], PPF, c["height"], S.mirror[i]) for i in range(4)]


def base_image():
    S = st.session_state
    return S.ai_img if S.ai_img is not None else S.realistic


def prefs_dict():
    p = st.session_state.prefs
    return {"mix": p["mix"], "effort": p["effort"], "harvest": p["harvest"], "kids_pets": p["kids_pets"]}


def draw_points(img, pts, maxw=900, rect=False, closed=False):
    s = min(1.0, maxw / img.shape[1])
    disp = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA).copy()
    Pp = [(int(x * s), int(y * s)) for x, y in pts]
    if rect and len(Pp) == 2:
        cv2.rectangle(disp, Pp[0], Pp[1], (0, 255, 0), 2)
    elif len(Pp) > 1:
        cv2.polylines(disp, [np.array(Pp)], closed and len(Pp) == 4, (0, 255, 0), 2)
    for i, p in enumerate(Pp):
        cv2.circle(disp, p, 6, (0, 0, 255), -1)
        cv2.putText(disp, str(i + 1), (p[0] + 9, p[1] - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    return rc.to_pil(disp)


def floor_area_sqft():
    S = st.session_state
    if S.info:
        return S.info["floor_w"] * S.info["floor_h"] / PPF / PPF
    try:
        return rc.compute_corners(S.cfg["L"], S.cfg["diag"] if S.cfg["use_diag"] else None)[1]
    except ValueError:
        return 0.0


# ================================================================= project save/load
def project_dict():
    S = st.session_state
    return {"version": 2, "roof": S.roof, "cfg": S.cfg, "site": S.site, "mirror": S.mirror,
            "quads": {str(k): v for k, v in S.quads.items()}, "cells": S.cells,
            "tap": list(S.tap) if S.tap else None, "prefs": S.prefs, "seed": S.seed, "chosen": S.chosen,
            "fl": S.fl, "grid_ft": GRID_FT,
            "note": "Photos are not stored in this file. Re-upload them in step 2."}


def apply_project(d):
    S = st.session_state
    S.cfg, S.site, S.mirror = d["cfg"], d["site"], d["mirror"]
    S.roof = d.get("roof") or {"block": None, "diff_ft": 10.0, "floors": [5, 6], "openings": []}
    S.demo_strips = None
    S.quads = {int(k): v for k, v in d["quads"].items()}
    S.cells = d.get("cells", {})
    S.tap = tuple(d["tap"]) if d.get("tap") else None
    S.prefs, S.seed, S.chosen = d["prefs"], d.get("seed", 1), d.get("chosen")
    S.fl = d.get("fl", S.fl)
    S.realistic, S.info, S.ai_img, S.options, S.opt_sig = None, None, None, {}, None
    for k in list(S.keys()):
        if k in ("H", "UD", "DG", "city", "lat", "lon", "bearing", "L0", "L1", "L2", "L3", "rf_block", "rf_corner", "rf_w", "rf_d", "rf_diff", "rf_f1",
                 "rf_f2", "rf_stair", "rf_sface", "rf_spos", "rf_door", "rf_dface", "rf_dpos") or k.startswith("pf_"):
            S.pop(k, None)


def summary_panel():
    S = st.session_state
    sb = st.sidebar
    sb.markdown("---")
    sb.subheader("Project summary")
    c = S.cfg
    sb.caption("Edges (ft): " + " · ".join(f"S{i + 1} {v:g}" for i, v in enumerate(c["L"])))
    sb.caption(f"Total floor area: {floor_area_sqft():.0f} sq ft")
    if S.info and S.cells:
        t = {r["Type"]: r["Area (sq ft)"] for r in rc.area_table(S.info, GRID_FT, S.cells)}
        usable = sum(t.get(f"{x.emoji} {x.label}", 0) for x in rc.TYPES if x.code in P.PLANT_ZONES)
        sb.caption(f"Usable for planting: {usable:.0f} sq ft")
        for x in rc.TYPES:
            a = t.get(f"{x.emoji} {x.label}", 0)
            if a:
                sb.caption(f"{x.emoji} {x.label}: {a:.0f} sq ft")
    b = S.site["bearing"]
    sb.caption(f"Side 1 faces {b:.0f}° ({rc.compass_name(b)}) · {S.site['city']}")
    sb.caption(f"North points {rc.north_angle_deg(b):.0f}° clockwise from 'up' on the plan")


def status_sidebar():
    S = st.session_state
    done = [True, all(im is not None for im in S.imgs) or S.demo_strips is not None, strips_ready() or S.demo_strips is not None, S.floor_sample is not None or S.demo_strips is not None,
            S.realistic is not None, len(S.cells) > 0, True, S.realistic is not None and len(S.cells) > 0,
            bool(S.options), S.chosen is not None]
    st.sidebar.title("🌿 Rooftop Garden Planner")
    st.sidebar.button("▶ Try the demo roof", on_click=load_demo, type="primary", width="stretch",
                      help="Loads a sample two-level roof (5th + 6th floor) so you can see everything in a minute.")
    st.sidebar.radio("Steps", STEPS, key="step")
    for name, d in zip(STEPS, done):
        st.sidebar.caption(("✅ " if d else "⬜ ") + name)
    summary_panel()
    st.sidebar.markdown("---")
    st.sidebar.info("🔒 **Privacy:** photos and plans stay in this browser session only. Nothing is stored on a server; "
                    "use *Save project* to keep your work. Don't upload photos showing people.")
    st.sidebar.download_button("💾 Save project (JSON)", json.dumps(project_dict(), indent=2),
                               "garden_project.json", "application/json")
    up = st.sidebar.file_uploader("Load project (JSON)", type=["json"], key="proj_up")
    if up is not None and st.sidebar.button("Load this project"):
        try:
            apply_project(json.loads(up.getvalue()))
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Could not load: {e}")
    if st.sidebar.button("Start over (clear everything)"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ================================================================= step 1
def step_size():
    S = st.session_state
    c, site = S.cfg, S.site
    st.header("1 · Roof & site")
    st.write("Side lengths in feet, in the order you walked (roof centre on your left). "
             "Side 1 = A→B (bottom edge of the plan), Side 2 = B→C, Side 3 = C→D, Side 4 = D→A.")
    col1, col2 = st.columns(2)
    with col1:
        for i in range(4):
            S.setdefault(f"L{i}", float(c["L"][i]))
            c["L"][i] = st.number_input(f"Side {i + 1} length (ft)", 1.0, 500.0, step=0.5, key=f"L{i}")
        S.setdefault("H", float(c["height"]))
        c["height"] = st.number_input("Railing / wall height (ft)", 1.0, 10.0, step=0.5, key="H")
        S.setdefault("UD", bool(c["use_diag"]))
        c["use_diag"] = st.checkbox("I measured the diagonal A→C (needed if the roof is not a rectangle)", key="UD")
        if c["use_diag"]:
            S.setdefault("DG", float(c["diag"]))
            c["diag"] = st.number_input("Diagonal A→C (ft)", 1.0, 700.0, step=0.5, key="DG")
        st.markdown("**Site**")
        S.setdefault("city", site["city"])
        site["city"] = st.text_input("City / place", key="city")
        S.setdefault("lat", float(site["lat"]))
        S.setdefault("lon", float(site["lon"]))
        a, b = st.columns(2)
        site["lat"] = a.number_input("Latitude", -90.0, 90.0, step=0.01, key="lat", format="%.2f")
        site["lon"] = b.number_input("Longitude", -180.0, 180.0, step=0.01, key="lon", format="%.2f")
        S.setdefault("bearing", float(site["bearing"]))
        site["bearing"] = st.number_input(
            "Compass bearing Side 1 faces (0=N, 90=E, 180=S, 270=W)", 0.0, 359.9, step=1.0, key="bearing",
            help="Stand in the middle of the roof, face the Side 1 railing, and read your phone compass.")
    with col2:
        try:
            corners, area, note = rc.compute_corners(c["L"], c["diag"] if c["use_diag"] else None)
            st.image(rc.to_pil(rc.outline_image(corners, bearing=site["bearing"])), caption="Roof outline with compass")
            st.success(f"Floor area ≈ {area:.1f} sq ft")
            st.caption(note)
            if c["use_diag"]:
                w, h = (c["L"][0] + c["L"][2]) / 2, (c["L"][1] + c["L"][3]) / 2
                if abs(c["diag"] - math.hypot(w, h)) > 1:
                    st.warning("Steps 5-10 currently treat the roof as a rectangle. The outline above is exact, "
                               "but the realistic image and garden plan will be approximate.")
        except ValueError as e:
            st.error(str(e))
    with st.expander("🏢 Two-level roof (5th floor + 6th-floor stair-house block)", expanded=two_level()):
        r = S.roof
        S.setdefault("rf_block", bool(r.get("block")))
        has = st.checkbox("Part of the roof is higher (e.g. the 6th floor sits on top of the staircase)", key="rf_block")
        if has:
            b = r.get("block") or {"w": 8.0, "d": 8.0, "corner": "C"}
            S.setdefault("rf_corner", b["corner"])
            S.setdefault("rf_w", float(b["w"]))
            S.setdefault("rf_d", float(b["d"]))
            S.setdefault("rf_diff", float(r.get("diff_ft", 10.0)))
            S.setdefault("rf_f1", int(r.get("floors", [5, 6])[0]))
            S.setdefault("rf_f2", int(r.get("floors", [5, 6])[1]))
            a1, a2, a3 = st.columns(3)
            corner = a1.selectbox("Corner holding the higher block", ["A", "B", "C", "D"], key="rf_corner",
                                  help="A = bottom-left, B = bottom-right, C = top-right, D = top-left on the plan.")
            bw = a2.number_input("Block width (ft)", 2.0, 400.0, step=0.5, key="rf_w")
            bd = a3.number_input("Block depth (ft)", 2.0, 400.0, step=0.5, key="rf_d")
            d1, d2, d3 = st.columns(3)
            diff = d1.number_input("Height difference (ft)", 3.0, 30.0, step=0.5, key="rf_diff")
            f1 = d2.number_input("Lower roof floor", 1, 30, key="rf_f1")
            f2 = d3.number_input("Higher roof floor", 1, 31, key="rf_f2")
            ops = []
            st.markdown("**How you get up**")
            S.setdefault("rf_stair", any(o["kind"] == "outer_stair" for o in r.get("openings", [])) or not r.get("openings"))
            S.setdefault("rf_door", any(o["kind"] == "door" for o in r.get("openings", [])) or not r.get("openings"))
            old = {o["kind"]: o for o in r.get("openings", [])}
            e1, e2 = st.columns(2)
            with e1:
                if st.checkbox("Small outer stair from the lower roof to the higher roof", key="rf_stair"):
                    o = old.get("outer_stair", {"face": "S", "pos_ft": 4.0})
                    S.setdefault("rf_sface", o["face"]); S.setdefault("rf_spos", float(o["pos_ft"]))
                    sf = st.selectbox("Stair on the block's wall facing", ["N", "S", "E", "W"], key="rf_sface")
                    sp = st.number_input("Distance along that wall (ft)", 0.0, 400.0, step=0.5, key="rf_spos")
                    ops.append({"kind": "outer_stair", "face": sf, "pos_ft": sp, "width_ft": 3.0})
            with e2:
                if st.checkbox("Door of the stair house (stairs are under the higher roof)", key="rf_door"):
                    o = old.get("door", {"face": "W", "pos_ft": 4.0})
                    S.setdefault("rf_dface", o["face"]); S.setdefault("rf_dpos", float(o["pos_ft"]))
                    df_ = st.selectbox("Door on the block's wall facing", ["N", "S", "E", "W"], key="rf_dface")
                    dp = st.number_input("Distance along that wall (ft)", 0.0, 400.0, step=0.5, key="rf_dpos")
                    ops.append({"kind": "door", "face": df_, "pos_ft": dp, "width_ft": 3.0})
            S.roof = {"block": {"w": bw, "d": bd, "corner": corner}, "diff_ft": diff, "floors": [int(f1), int(f2)], "openings": ops}
            errs = RM.validate(roof_now())
            for e in errs:
                st.error(e)
            if not errs:
                A = RM.areas(roof_now())
                st.success(f"{f1}th floor roof: {A[1]:.0f} sq ft · {f2}th floor roof: {A[2]:.0f} sq ft")
            if S.roof["block"] and not any(o["kind"] == "outer_stair" for o in ops):
                st.warning("Without the outer stair, the higher roof is treated as unreachable and gets no plants.")
            st.caption("The step between the roofs is shown as a plain concrete wall. Walkways in front of the stair "
                       "and door are kept clear automatically.")
        else:
            S.roof = {"block": None, "diff_ft": 10.0, "floors": [5, 6], "openings": []}
    nav(0)


# ================================================================= step 2
def step_upload():
    S = st.session_state
    st.header("2 · Upload the 4 railing photos")
    st.write("One photo per side, same order as the lengths. Each should show the whole railing end to end.")
    cols = st.columns(4)
    for i in range(4):
        with cols[i]:
            st.subheader(f"Side {i + 1}")
            f = st.file_uploader(f"Photo for side {i + 1}", type=["jpg", "jpeg", "png", "webp"],
                                 key=f"up_{i}", label_visibility="collapsed")
            if f is not None:
                sig = (f.name, f.size)
                if S.get(f"upsig_{i}") != sig:
                    first = S.get(f"upsig_{i}") is None
                    S.imgs[i] = rc.decode_image(f.getvalue())
                    S[f"upsig_{i}"] = sig
                    if not (first and len(S.quads[i]) == 4):      # keep loaded clicks for a first upload
                        S.quads[i] = []
                    S.realistic = None
            if S.imgs[i] is not None:
                st.image(rc.to_pil(S.imgs[i]), width="stretch")
                st.caption("✅ loaded")
    nav(1)


# ================================================================= step 3
def step_mark():
    S = st.session_state
    st.header("3 · Mark the railing in each photo")
    if any(im is None for im in S.imgs):
        st.warning("Upload all 4 photos in step 2 first.")
        nav(2)
        return
    labels = [f"Side {i + 1} {'✅' if len(S.quads[i]) == 4 else '⬜'}" for i in range(4)]
    side = st.radio("Photo", range(4), index=S.side, format_func=lambda i: labels[i], horizontal=True)
    S.side = side
    pts, img = S.quads[side], S.imgs[side]
    left, right = st.columns([3, 2])
    with left:
        if len(pts) < 4:
            st.info(f"**Click point {CORNER_HELP[len(pts)]}** on the railing "
                    "(top-left → top-right → bottom-right → bottom-left, as seen in the photo).")
        else:
            st.success("All 4 corners set. The green outline should hug the railing.")
        val = img_click(draw_points(img, pts, closed=True), key=f"rail_{side}")
        v = fresh_click(f"rail_{side}", val)
        if v and len(pts) < 4:
            sc = img.shape[1] / v["width"]
            pts.append([v["x"] * sc, v["y"] * sc])
            S.realistic = None
            st.rerun()
        b1, b2, b3 = st.columns(3)
        if b1.button("↩ Undo last point", disabled=not pts):
            pts.pop()
            S.realistic = None
            st.rerun()
        if b2.button("🗑 Reset this photo", disabled=not pts):
            S.quads[side] = []
            S.realistic = None
            st.rerun()
        if b3.button("Next photo ▶", disabled=len(pts) < 4 or side == 3):
            S.side = side + 1
            st.rerun()
    with right:
        st.subheader("Straightened railing preview")
        S.mirror[side] = st.checkbox("Mirror left↔right (use if the railing looks reversed in the final image)",
                                     value=S.mirror[side], key=f"mir_{side}")
        if len(pts) == 4:
            strip = rc.make_strip(img, pts, S.cfg["L"][side], PPF, S.cfg["height"], S.mirror[side])
            st.image(rc.to_pil(strip), width="stretch", caption=f"{S.cfg['L'][side]} ft × {S.cfg['height']} ft")
        else:
            st.caption("The preview appears after the 4th click.")
    nav(2)


# ================================================================= step 4
def step_floor():
    S = st.session_state
    st.header("4 · Floor sample (optional, makes the floor realistic)")
    if any(im is None for im in S.imgs):
        st.warning("Upload the photos in step 2 first.")
        nav(3)
        return
    st.write("Click **two opposite corners** of a flat piece of real floor (no railing, shadow or pots). "
             "You can skip this and use a generated concrete floor.")
    src = st.radio("Take the sample from photo", range(4), index=S.floor_src,
                   format_func=lambda i: f"Side {i + 1}", horizontal=True)
    if src != S.floor_src:
        S.floor_src, S.floor_pts = src, []
        st.rerun()
    img = S.imgs[src]
    left, right = st.columns([3, 2])
    with left:
        st.info(f"Click corner {len(S.floor_pts) + 1} of 2" if len(S.floor_pts) < 2 else "Area selected.")
        val = img_click(draw_points(img, S.floor_pts, rect=True), key=f"floor_{src}")
        v = fresh_click(f"floor_{src}", val)
        if v and len(S.floor_pts) < 2:
            sc = img.shape[1] / v["width"]
            S.floor_pts.append([v["x"] * sc, v["y"] * sc])
            if len(S.floor_pts) == 2:
                (x0, y0), (x1, y1) = S.floor_pts
                xa, xb, ya, yb = int(min(x0, x1)), int(max(x0, x1)), int(min(y0, y1)), int(max(y0, y1))
                if xb - xa >= 10 and yb - ya >= 10:
                    S.floor_sample = img[ya:yb, xa:xb].copy()
                else:
                    S.floor_pts = []
                    st.warning("That area is too small. Try again.")
            S.realistic = None
            st.rerun()
        if st.button("🗑 Clear selection"):
            S.floor_pts, S.floor_sample, S.realistic = [], None, None
            st.rerun()
    with right:
        if S.floor_sample is not None:
            st.image(rc.to_pil(S.floor_sample), caption="Floor sample used", width="stretch")
        else:
            st.caption("No sample: a generated concrete floor will be used.")
        fl = S.fl
        st.subheader("Floor settings")
        fl["tex"] = st.slider("Real-world width the sample covers (ft)", 1.0, 10.0, float(fl["tex"]), 0.5)
        fl["joint"] = st.slider("Expansion joint spacing (ft, 0 = none)", 0.0, 20.0, float(fl["joint"]), 1.0)
        fl["seed"] = st.number_input("Texture variation (seed)", 0, 9999, int(fl["seed"]))
        if S.floor_sample is None:
            fl["base"] = st.color_picker("Generated floor colour", fl["base"])
    nav(3)


# ================================================================= step 5
AI_PROMPT = ("This is a top-down layout of a rooftop. The center rectangle is the roof floor, and the four surrounding "
             "bands are the inside faces of the parapet walls and railings, folded outward. Keep the exact layout, "
             "proportions, and positions of all four walls, and keep the wall and railing textures. Make the whole "
             "image look like one seamless, realistic top-down photograph. Remove any hard seams and diagonal lines at "
             "the corners. Make the floor realistic weathered concrete with fine grain, small cracks, subtle stains, "
             "soft shadows along the walls, and natural daylight. Do not add any plants, furniture, text, or labels. "
             "Do not change the size or shape of the roof.")


def step_realistic():
    S = st.session_state
    st.header("5 · Realistic image")
    if not strips_ready() and S.demo_strips is None:
        st.warning("Finish steps 2 and 3 first (4 photos, 4 corners each), or press **Try the demo roof** in the sidebar.")
        nav(4)
        return
    hexc = S.fl["base"].lstrip("#")
    base_bgr = (int(hexc[4:6], 16), int(hexc[2:4], 16), int(hexc[0:2], 16))
    if st.button("🎨 Generate / refresh realistic image", type="primary"):
        with st.spinner("Rendering..."):
            S.realistic, S.info = rc.render_realistic(
                strips_any(), S.cfg["L"], PPF, floor_sample=S.floor_sample, seed=int(S.fl["seed"]),
                joint_ft=S.fl["joint"], tex_scale_ft=S.fl["tex"], base_bgr=base_bgr)
            if S.get("cells_info") != S.info:
                S.cells, S.tap, S.options = {}, None, {}
            S.cells_info = dict(S.info)
    if S.realistic is None:
        st.caption("Click the button to build the image.")
    else:
        shown = rc.draw_compass(S.realistic.copy(), S.site["bearing"])
        st.image(rc.to_pil(shown), width="stretch", caption="With compass (the download below is clean)")
        d1, d2 = st.columns(2)
        d1.download_button("⬇ Clean PNG (for AI tools)", rc.encode_png(S.realistic), "layout_realistic.png", "image/png")
        d2.download_button("⬇ PNG with compass", rc.encode_png(shown), "layout_compass.png", "image/png")
        with st.expander("Want it more photographic? Use an AI image tool (optional)"):
            st.write("Upload the clean PNG to ChatGPT, Gemini or Adobe Firefly with this prompt:")
            st.code(AI_PROMPT, language=None)
            st.write("Then upload the improved image here. It must keep the **same layout and aspect ratio**.")
            f = st.file_uploader("AI-improved image", type=["png", "jpg", "jpeg"], key="ai_up")
            if f is not None:
                im = rc.decode_image(f.getvalue(), max_side=4000)
                S.ai_img = cv2.resize(im, (S.info["image_w"], S.info["image_h"]), interpolation=cv2.INTER_AREA)
                st.image(rc.to_pil(S.ai_img), caption="Will be used as the base for later steps (resized)", width="stretch")
            if S.ai_img is not None and st.button("Remove AI image"):
                S.ai_img = None
                st.rerun()
    nav(4)


# ================================================================= step 6
def push_undo():
    S = st.session_state
    S.undo.append(dict(S.cells))
    S.undo = S.undo[-60:]


@dialog("Choose a type for this cell")
def choose_type(r, c):
    S = st.session_state
    st.write(f"Cell: row {r + 1}, column {c + 1} ({c * GRID_FT}–{(c + 1) * GRID_FT} ft from left, "
             f"{r * GRID_FT}–{(r + 1) * GRID_FT} ft from top)")
    cols = st.columns(2)
    for i, t in enumerate(rc.TYPES):
        if cols[i % 2].button(f"{t.emoji} {t.label}", key=f"dlg_{i}", width="stretch"):
            push_undo()
            S.cells[f"{r},{c}"] = t.code
            st.rerun()
    if st.button("🧽 Clear this cell", key="dlg_clear", width="stretch"):
        push_undo()
        S.cells.pop(f"{r},{c}", None)
        st.rerun()


def step_grid():
    S = st.session_state
    st.header("6 · Grid & types")
    if S.realistic is None:
        st.warning("Generate the realistic image in step 5 first.")
        nav(5)
        return
    info, base = S.info, base_image()
    cols_n, rows_n, _ = rc.grid_dims(info, GRID_FT)
    st.caption(f"{GRID_FT} ft × {GRID_FT} ft grid: {cols_n} columns × {rows_n} rows. Row 1 is the top of the image. "
               "Mark the **water tap** too: the layout puts thirsty plants near it.")
    ctrl, main = st.columns([1, 3])
    with ctrl:
        mode = st.radio("How do you want to assign?",
                        ["✏️ Marker (brush / lasso)", "Pop-up per cell", "Paint with a type", "Fill a rectangle",
                         "Mark water tap"], key="mode")
        type_opts = [f"{t.emoji} {t.label}" for t in rc.TYPES] + ["🧽 Erase"]
        brush = None
        mtool, mrad, mover = "brush", 2.0, True
        if mode == "✏️ Marker (brush / lasso)":
            tools = {"Brush (circle)": "brush", "Lasso (freehand)": "lasso", "Polygon (click corners)": "polygon",
                     "Rectangle": "rect", "Circle": "circle"}
            mtool = tools[st.radio("Tool", list(tools), key="mtool")]
            if mtool == "brush":
                mrad = st.slider("Brush radius (ft)", 0.5, 8.0, 2.0, 0.5, key="mrad",
                                 help="The circle on the plan is drawn to scale: each small + mark is 2 ft.")
            brush = st.radio("Type to mark", type_opts, key="brush")
            mover = st.checkbox("Overwrite cells already marked", True, key="mover")
            st.caption("Drag to paint. Everything inside the circle or loop gets the type. "
                       "The + marks show the 2 ft × 2 ft grid, and the bar shows 10 ft.")
        elif mode in ("Paint with a type", "Fill a rectangle"):
            brush = st.radio("Type to apply", type_opts, key="brush")
        if mode == "Fill a rectangle":
            st.caption("Click one corner cell, then the opposite corner cell.")
            if S.anchor and st.button("Cancel rectangle"):
                S.anchor = None
                st.rerun()
        if mode == "Mark water tap":
            st.caption("Click the cell where the tap is.")
            if S.tap and st.button("Remove tap marker"):
                S.tap = None
                st.rerun()
        st.markdown("---")
        b1, b2, b3 = st.columns(3)
        if b1.button("↩ Undo", disabled=not S.undo):
            S.redo.append(dict(S.cells))
            S.cells = S.undo.pop()
            st.rerun()
        if b2.button("↪ Redo", disabled=not S.redo):
            S.undo.append(dict(S.cells))
            S.cells = S.redo.pop()
            st.rerun()
        if b3.button("🗑 Clear", disabled=not S.cells):
            push_undo()
            S.cells = {}
            st.rerun()
        if two_level() or True:
            if st.button("☀️ Suggest sun/shade from the sun path", width="stretch",
                         help="Computes which cells the higher block shades in the planting month. You can edit the result."):
                push_undo()
                S.cells = SUN.suggest_types(roof_now(), S.site["lat"], S.prefs["month"], S.site["bearing"], GRID_FT)
                S.options = {}
                S.paint_msg = ("Suggested from the sun path for " + P.MONTH_NAMES[S.prefs["month"] - 1] +
                               ". Cells in the block's shadow became Shade / Morning / Afternoon Sun.")
                st.rerun()
        fill_opts = [f"{t.emoji} {t.label}" for t in rc.TYPES]
        fill = st.selectbox("Fill all unassigned cells with", fill_opts, key="fillsel")
        if st.button("Fill unassigned"):
            push_undo()
            code = rc.TYPES[fill_opts.index(fill)].code
            for r in range(rows_n):
                for c in range(cols_n):
                    S.cells.setdefault(f"{r},{c}", code)
            st.rerun()
    with main:
        hl = [tuple(S.anchor)] if S.anchor else []
        overlay = show_overlay(rc.render_grid(base, info, GRID_FT, S.cells, highlight=hl, tap=S.tap, bearing=S.site["bearing"]))
        v = None
        if S.paint_msg:
            st.info(S.paint_msg)
        if mode == "✏️ Marker (brush / lasso)":
            code = None if brush == "🧽 Erase" else rc.TYPES[type_opts.index(brush)].code
            col = (0, 0, 0) if code is None else rc.BY_CODE[code].bgr[::-1]
            sig = json.dumps([S.cells, S.tap, roof_now()["W"], S.roof], sort_keys=True, default=str)
            res = S.pop("_test_paint", None) or painter(data_url(overlay, 80), "img" + str(abs(hash(sig))), info, GRID_FT,
                                                       mtool, mrad, col, "Erase" if code is None else rc.BY_CODE[code].label,
                                                       key="painter")
            if res and res.get("nonce") != S.get("last_nonce"):
                S.last_nonce = res["nonce"]
                sel = PT.select({"tool": res["tool"], "points": res["points"], "radius_ft": res.get("radius_ft", mrad)},
                                info, GRID_FT)
                allowed = {RM.key(c) for lv in RM.level_cells(roof_now(), GRID_FT).values() for c in lv}
                new, n = PT.apply_selection(S.cells, sel, code, mover, allowed)
                if n:
                    push_undo()
                    S.redo = []
                    S.cells = new
                    S.options = {}
                S.paint_msg = (f"{'Erased' if code is None else 'Marked'} {n} cells ({n * GRID_FT * GRID_FT:g} sq ft)"
                               f" · tool: {res['tool']}")
                st.rerun()
        else:
            S.paint_msg = ""
            val = img_click(rc.to_pil(overlay), key="gridclick")
            v = fresh_click("gridclick", val)
        if v:
            sc = info["image_w"] / v["width"]
            hit = rc.cell_from_xy(info, GRID_FT, v["x"] * sc, v["y"] * sc)
            if hit is not None:
                r, c = hit
                if mode == "Pop-up per cell":
                    choose_type(r, c)
                elif mode == "Mark water tap":
                    S.tap = (r, c)
                    S.options = {}
                    st.rerun()
                else:
                    code = None if brush == "🧽 Erase" else rc.TYPES[type_opts.index(brush)].code
                    if mode == "Paint with a type":
                        push_undo()
                        if code is None:
                            S.cells.pop(f"{r},{c}", None)
                        else:
                            S.cells[f"{r},{c}"] = code
                        st.rerun()
                    elif S.anchor is None:
                        S.anchor = (r, c)
                        st.rerun()
                    else:
                        push_undo()
                        r0, c0 = S.anchor
                        for rr in range(min(r0, r), max(r0, r) + 1):
                            for cc in range(min(c0, c), max(c0, c) + 1):
                                if code is None:
                                    S.cells.pop(f"{rr},{cc}", None)
                                else:
                                    S.cells[f"{rr},{cc}"] = code
                        S.anchor = None
                        st.rerun()
    st.subheader("Summary")
    st.dataframe(pd.DataFrame(rc.area_table(info, GRID_FT, S.cells)), hide_index=True, width="stretch")
    d1, d2, d3 = st.columns(3)
    data = rc.export_dict(info, GRID_FT, S.cells)
    data["water_tap_cell"] = list(S.tap) if S.tap else None
    data["side1_bearing_deg"] = S.site["bearing"]
    d1.download_button("⬇ Grid data (JSON)", json.dumps(data, indent=2), "grid_types.json", "application/json")
    d2.download_button("⬇ Grid data (CSV)", rc.cells_csv(info, GRID_FT, S.cells), "grid_cells.csv", "text/csv")
    d3.download_button("⬇ Overlay image (PNG)", rc.encode_png(overlay), "grid_overlay.png", "image/png")
    nav(5)


# ================================================================= step 7
def step_prefs():
    S = st.session_state
    p = S.prefs
    st.header("7 · Preferences")
    st.write("Tell us what the customer wants. Sliders are relative shares (they are normalised to 100%).")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Garden mix**")
        for key, label in (("vegetable", "Vegetables"), ("flower", "Flowers"), ("fruit", "Fruit (lemon, guava…)"),
                           ("herb", "Herbs"), ("ornamental", "Foliage / ornamental")):
            S.setdefault(f"pf_{key}", int(p["mix"][key]))
            p["mix"][key] = st.slider(label, 0, 100, key=f"pf_{key}")
        tot = sum(p["mix"].values()) or 1
        st.caption("Resulting shares: " + ", ".join(f"{k} {100 * v / tot:.0f}%" for k, v in p["mix"].items() if v))
        S.setdefault("pf_effort", p["effort"])
        p["effort"] = st.radio("How much time can you give?", ["daily", "weekends", "managed"], key="pf_effort",
                               format_func={"daily": "Daily care is fine", "weekends": "Weekends only",
                                            "managed": "Fully managed by us"}.get, horizontal=True)
        S.setdefault("pf_harvest", p["harvest"])
        p["harvest"] = st.radio("Main purpose", ["home", "sell", "decor"], key="pf_harvest",
                                format_func={"home": "Cooking at home", "sell": "Selling produce",
                                             "decor": "Decoration only"}.get, horizontal=True)
        S.setdefault("pf_kids", p["kids_pets"])
        p["kids_pets"] = st.checkbox("Children or pets use the roof (avoid thorny / toxic plants)", key="pf_kids")
    with c2:
        S.setdefault("pf_budget", float(p["budget"]))
        p["budget"] = st.number_input("Budget (BDT)", 0.0, 10_000_000.0, step=1000.0, key="pf_budget")
        S.setdefault("pf_style", p["style"])
        p["style"] = st.selectbox("Style (stored for the designer)", ["Modern", "Traditional", "Wild", "Minimal"],
                                  key="pf_style")
        S.setdefault("pf_month", p["month"])
        p["month"] = st.selectbox("Planting month", range(1, 13), key="pf_month",
                                  format_func=lambda m: P.MONTH_NAMES[m - 1])
        S.setdefault("pf_load", float(p["load_limit"]))
        p["load_limit"] = st.number_input("Allowed extra roof load (kg/m²)", 20.0, 600.0, step=10.0, key="pf_load",
                                          help="Ask a structural engineer. The app only warns, it does not certify safety.")
        S.setdefault("pf_labour", float(p["labour"]))
        p["labour"] = st.number_input("Installation labour (% of materials)", 0.0, 100.0, step=1.0, key="pf_labour")
        if not S.cells:
            st.warning("No grid types assigned yet. Do step 6 first.")
    nav(6)


# ================================================================= step 8
def step_candidates():
    S = st.session_state
    st.header("8 · Candidate plants per zone")
    if not S.cells:
        st.warning("Assign grid types in step 6 first.")
        nav(7)
        return
    df = get_plants()
    st.caption(f"Month: {P.MONTH_NAMES[S.prefs['month'] - 1]}. Ranked by your preferences, season and light. "
               "⚠️ All plant data is a starter set and needs agronomist review.")
    counts = {}
    for z in S.cells.values():
        counts[z] = counts.get(z, 0) + 1
    shown = False
    for z in P.PLANT_ZONES:
        if z not in counts:
            continue
        shown = True
        t = rc.BY_CODE[z]
        with st.expander(f"{t.emoji} {t.label}: {counts[z]} cells", expanded=True):
            cdf = P.candidates_for_zone(df, z, S.prefs["month"], prefs_dict())
            if len(cdf):
                st.dataframe(cdf.drop(columns=["id"]).head(10), hide_index=True, width="stretch")
            else:
                st.info("No plants fit this zone in this month. Consider a shade net or a different month.")
    for z in ("BLOCKED", "WALKWAY"):
        if z in counts:
            st.caption(f"{rc.BY_CODE[z].emoji} {rc.BY_CODE[z].label}: {counts[z]} cells (nothing planted)")
    if not shown:
        st.info("No sun/shade zones assigned yet.")
    nav(7)


# ================================================================= step 9
def options_signature():
    S = st.session_state
    return json.dumps([S.cells, S.prefs, S.tap, S.site["bearing"], S.seed, S.roof], sort_keys=True, default=str)


def run_options():
    S = st.session_state
    df, mats = get_plants(), get_materials()
    nv = rc.north_vector(S.site["bearing"])
    roof = roof_now()
    taps = {RM.level_of_cell(roof, S.tap[0], S.tap[1], GRID_FT): S.tap} if S.tap else {}
    S.options = {}
    for v in L.VARIANTS:
        res = L.generate_roof(roof, S.cells, df, prefs_dict(), S.prefs["month"], v, nv, taps=taps, seed=S.seed,
                              grid_ft=GRID_FT)
        res["metrics"] = L.metrics_roof(res["placements"], df, roof, S.prefs["load_limit"], nv)
        res["bom"], res["total"] = L.build_bom(res["placements"], df, mats, S.prefs["labour"])
        S.options[v] = res
    S.opt_sig = options_signature()


def choose_option(name):
    st.session_state.chosen = name
    st.session_state.step = STEPS[9]


def step_options():
    S = st.session_state
    st.header("9 · Garden options")
    if S.realistic is None or not S.cells:
        st.warning("Finish steps 5 and 6 first (realistic image and grid types).")
        nav(8)
        return
    df = get_plants()
    b1, b2, _ = st.columns([1, 1, 4])
    if b1.button("🌱 Generate 3 options", type="primary"):
        with st.spinner("Designing..."):
            run_options()
    if b2.button("🔀 Reshuffle"):
        S.seed += 1
        with st.spinner("Designing..."):
            run_options()
    if not S.options:
        st.caption("Click Generate to create Productive, Colorful and Balanced layouts.")
        nav(8)
        return
    if S.opt_sig != options_signature():
        st.warning("Your inputs changed after these options were made. Click Generate to refresh.")
    cols = st.columns(3)
    base = base_image()
    for col, (name, res) in zip(cols, S.options.items()):
        m = res["metrics"]
        with col:
            st.subheader(name)
            st.caption(L.VARIANTS[name]["desc"])
            img = show_overlay(pr.render_plan(base, S.info, GRID_FT, S.cells, res["placements"], df, bearing=S.site["bearing"],
                                              tap=S.tap, labels=False, legend=False))
            st.image(rc.to_pil(img), width="stretch")
            st.metric("Estimated cost (BDT)", f"{res['total']:,.0f}")
            a, b = st.columns(2)
            a.metric("Planters", m["planters"])
            b.metric("Plants", m["plants"])
            a.metric("Care (h/week)", m["effort_h_week"])
            b.metric("Added load (kg/m²)", m["avg_load"])
            if res["total"] > S.prefs["budget"] > 0:
                st.warning(f"Over your budget of {S.prefs['budget']:,.0f} BDT.")
            for w in m["warnings"]:
                st.warning(w)
            for n in res["notes"][:4] + m["advice"][:2]:
                st.caption("• " + n)
            st.button(f"✅ Choose {name}", key=f"choose_{name}", on_click=choose_option, args=(name,),
                      type="primary" if S.chosen == name else "secondary")
    st.caption("Layout rules: tall plants on the north side, thirsty plants near the tap, a path to every planter. "
               "Plant data is unverified until an agronomist reviews data/plants.csv.")
    nav(8)


# ================================================================= step 10
def step_final():
    S = st.session_state
    st.header("10 · Final plan")
    if not S.options:
        st.warning("Generate options in step 9 first.")
        nav(9)
        return
    name = S.chosen if S.chosen in S.options else list(S.options)[0]
    res = S.options[name]
    df = get_plants()
    m = res["metrics"]
    st.subheader(f"{name} option")
    c = st.columns(5)
    c[0].metric("Estimated cost (BDT)", f"{res['total']:,.0f}")
    c[1].metric("Planters", m["planters"])
    c[2].metric("Species", m["species"])
    c[3].metric("Care (h/week)", m["effort_h_week"])
    c[4].metric("Added load (kg/m²)", m["avg_load"])
    for w in m["warnings"]:
        st.warning(w)
    with st.expander("Care and safety advice"):
        for a in m["advice"]:
            st.write("• " + a)
    base = base_image()
    plan = show_overlay(pr.render_plan(base, S.info, GRID_FT, S.cells, res["placements"], df, bearing=S.site["bearing"], tap=S.tap))
    t1, t2, t3, t4 = st.tabs(["🗺 Top view", "🧊 3D impression", "📋 Plants & BOM", "⬇ Export"])
    with t1:
        st.image(rc.to_pil(plan), width="stretch")
    with t2:
        stage = st.radio("Growth stage", list(pr.STAGE_K), index=2, horizontal=True, format_func=pr.STAGE_LABEL.get,
                         help="Shows how the garden looks on planting day, after about 3 months, and fully grown.")
        roof = roof_now()
        strips = strips_any()
        I = S.info
        floor = base[I["floor_y0"]:I["floor_y0"] + I["floor_h"], I["floor_x0"]:I["floor_x0"] + I["floor_w"]]
        sc = build_scene(roof, res["placements"], df, S.site["lat"], S.prefs["month"], S.site["bearing"],
                         SUN.north_plan(S.site["bearing"]), GRID_FT, strips=strips, floor_bgr=floor, stage=stage,
                         rail_ft=S.cfg["height"], hour=10.0)
        sid = json.dumps([S.chosen, S.seed, stage, S.roof, len(res["placements"]), S.site["bearing"], S.prefs["month"]], default=str)
        viewer3d(sc, sid, height=560, key="v3d")
        d3 = None
        st.caption("Illustrative impression only: simple shapes, not exact plants or sizes. Drag to rotate, scroll to zoom; "
                   "the slider inside the picture moves the sun for the planting month. The step between the two roofs is a plain concrete wall.")
    with t3:
        counts = {}
        for p in res["placements"]:
            counts[p["plant_id"]] = counts.get(p["plant_id"], 0) + 1
        rows = [{"Plant": df.loc[k, "name_en"], "বাংলা": df.loc[k, "name_bn"], "Category": df.loc[k, "category"], "Form": df.loc[k, "form"],
                 "Planters": v, "Plants": v * int(df.loc[k, "per_cell"]),
                 "Verified": "✅" if df.loc[k, "verified"] else "⚠️"} for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.markdown("**Bill of materials** (placeholder prices: edit `data/materials.csv` and `data/plants.csv`)")
        st.dataframe(res["bom"], hide_index=True, width="stretch")
        st.success(f"Total: {res['total']:,.0f} BDT")
        if S.prefs["budget"] and res["total"] > S.prefs["budget"]:
            st.warning(f"This is above the budget of {S.prefs['budget']:,.0f} BDT.")
    with t4:
        bearing_text = f"Side 1 faces {S.site['bearing']:.0f} degrees ({rc.compass_name(S.site['bearing'])})"
        st.download_button("⬇ Plan (PNG)", rc.encode_png(plan), f"plan_{name}.png", "image/png")
        st.download_button("⬇ Bill of materials (CSV)", res["bom"].to_csv(index=False), f"bom_{name}.csv", "text/csv")
        st.download_button("⬇ Placements (JSON)", json.dumps(res["placements"], indent=2), f"placements_{name}.json",
                           "application/json")
        st.download_button("⬇ Whole project (JSON)", json.dumps(project_dict(), indent=2), "garden_project.json",
                           "application/json")
        with st.expander("Prompt for an AI image tool (more photographic impression)"):
            st.code(L.ai_prompt(res["placements"], "", bearing_text, GRID_FT), language=None)
            st.caption("Attach the clean realistic image from step 5. Label results as an illustrative impression.")
    nav(9)


# ================================================================= main
init_state()
status_sidebar()
{1: step_size, 2: step_upload, 3: step_mark, 4: step_floor, 5: step_realistic, 6: step_grid,
 7: step_prefs, 8: step_candidates, 9: step_options, 10: step_final}[int(st.session_state.step.split(" ")[0])]()
