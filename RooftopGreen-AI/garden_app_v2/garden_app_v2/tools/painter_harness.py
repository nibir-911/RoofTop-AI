"""Developer harness: shows the painter component on a plain test image and prints what it returns."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, cv2, streamlit as st
import paint
from painter_component import painter, data_url

st.set_page_config(layout="wide")
info = {"floor_x0": 120, "floor_y0": 120, "floor_w": 800, "floor_h": 600, "ppf": 40, "image_w": 1040, "image_h": 840}
img = np.full((840, 1040, 3), 150, np.uint8)
cv2.rectangle(img, (120, 120), (920, 720), (190, 190, 185), -1)
tool = st.session_state.get("tool", "brush")
tool = st.radio("tool", ["brush", "lasso", "polygon", "rect", "circle"], horizontal=True, key="tool")
val = painter(data_url(img), "harness1", info, 2, tool, 2.0, (255, 215, 0), "Full Sun", key="p")
if val:
    sel = paint.select(val, info, 2)
    st.write("RESULT tool=%s points=%d cells=%d" % (val["tool"], len(val["points"]), len(sel)))
    st.session_state["last"] = sorted(sel)
