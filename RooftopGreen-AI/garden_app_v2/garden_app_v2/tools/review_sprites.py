"""Reviewer page: approve or reject candidate sprites. Run:  streamlit run tools/review_sprites.py
Approved sprites are copied to data/sprites/<plant_id>/ and appear in the garden app's 3D view."""
import glob, json, os, sys
import streamlit as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import sprites as SP

st.set_page_config(page_title="Sprite review", layout="wide")
st.title("Plant sprite review")
st.caption("Approve only if the picture is botanically correct for Bangladesh, shows the right growth stage, "
           "and has a clean cut-out. Only approved sprites are used in customer images.")
reviewer = st.text_input("Your name (stored in the manifest)")
files = sorted(f for f in glob.glob(os.path.join(ROOT, "data", "sprites_review", "*", "*.png")) if not f.endswith("_raw.png"))
if not files:
    st.info("No candidates yet. Run tools/make_sprites.py first.")
for f in files:
    meta = json.load(open(f[:-4] + ".json")) if os.path.exists(f[:-4] + ".json") else {}
    pid, stage = meta.get("plant_id", os.path.basename(os.path.dirname(f))), meta.get("stage", "mature")
    cur = SP.read_manifest(pid)["stages"].get(stage, {}).get("status", "none")
    c1, c2 = st.columns([1, 2])
    c1.image(f, width=220)
    c2.markdown(f"**{pid}** · stage **{stage}** · seed {meta.get('seed')} · current status: `{cur}`")
    c2.caption(meta.get("prompt", ""))
    b1, b2 = c2.columns(2)
    if b1.button("✅ Approve", key="a" + f, disabled=not reviewer):
        SP.approve(pid, stage, f, reviewer, meta.get("model", ""), meta.get("prompt", ""), meta.get("seed"))
        st.rerun()
    if b2.button("❌ Reject", key="r" + f):
        SP.reject(pid, stage)
        st.rerun()
