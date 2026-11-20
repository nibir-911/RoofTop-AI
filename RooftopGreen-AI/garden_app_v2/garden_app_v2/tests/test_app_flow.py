import os, sys
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from streamlit.testing.v1 import AppTest

def photo(i):
    img = np.zeros((800,1200,3),np.uint8); img[:300]=(235,206,135); img[300:520]=(120,140,160); img[520:]=(170,170,165)
    cv2.rectangle(img,(100,330),(1100,640),(40,40,160),6)
    for x in range(100,1101,50): cv2.line(img,(x,330),(x,640),(40,40,160),5)
    return img

def test_full_flow():
    imgs=[photo(i) for i in range(4)]
    quad=[[100,330],[1100,330],[1100,640],[100,640]]
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=120)
    at.session_state["imgs"]=imgs
    at.session_state["quads"]={i:[list(p) for p in quad] for i in range(4)}
    at.session_state["floor_sample"]=imgs[0][560:760,100:500]
    at.run(); assert not at.exception
    steps=["1 · Roof & site","2 · Upload photos","3 · Mark railings","4 · Floor sample"]
    for s in steps:
        at.session_state["step"]=s; at.run(); assert not at.exception, (s, at.exception)
    at.session_state["step"]="5 · Realistic image"; at.run()
    [b for b in at.button if "Generate" in b.label][0].click(); at.run(); assert not at.exception
    info=at.session_state["info"]
    cells={f"{r},{c}":("FULL_SUN" if r<3 else "MORNING_SUN" if c<5 else "SHADE") for r in range(8) for c in range(10)}
    cells["3,9"]="BLOCKED"; cells["7,0"]="WALKWAY"
    at.session_state["cells"]=cells; at.session_state["tap"]=(0,0)
    for s in ["6 · Grid & types","7 · Preferences","8 · Candidate plants"]:
        at.session_state["step"]=s; at.run(); assert not at.exception, (s, at.exception)
    at.session_state["step"]="9 · Garden options"; at.run()
    [b for b in at.button if "Generate 3" in b.label][0].click(); at.run(); assert not at.exception
    assert len(at.session_state["options"])==3
    for name,res in at.session_state["options"].items():
        pl=res["placements"]; zones={(p["row"],p["col"]) for p in pl}
        assert "3,9" not in {f"{r},{c}" for r,c in zones} and (7,0) not in zones   # nothing on blocked/walkway
        assert len(zones)==len(pl)
        assert abs(res["bom"]["Cost (BDT)"].sum()-res["total"])<1
    [b for b in at.button if b.label.startswith("✅ Choose Balanced")][0].click(); at.run(); assert not at.exception
    assert at.session_state["step"].startswith("10")
    print("final plan ok")
    # project save/load roundtrip
