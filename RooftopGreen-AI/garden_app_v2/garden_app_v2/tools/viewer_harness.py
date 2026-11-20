"""Headless test: render the 3D viewer with a sample scene and save a screenshot."""
import sys, json, threading, http.server, socketserver, functools, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, cv2
import roofmodel as RM, plants as PL, layout as LY, viewer3d_component as V
from playwright.sync_api import sync_playwright

root = RM.new_roof(20, 16, {"w": 8, "d": 8, "corner": "C"}, 10,
                   openings=[{"kind": "outer_stair", "face": "S", "pos_ft": 4, "width_ft": 3},
                             {"kind": "door", "face": "W", "pos_ft": 4, "width_ft": 3}])
df = PL.load_plants()
fake = [{"row": 1, "col": 1, "plant_id": df.index[0], "level": 1}, {"row": 2, "col": 3, "plant_id": df.index[5], "level": 1},
        {"row": 5, "col": 8, "plant_id": df.index[10], "level": 2}, {"row": 6, "col": 5, "plant_id": df.index[20], "level": 1}]
floor = np.full((200, 250, 3), (160, 170, 165), np.uint8)
strip = np.full((60, 400, 3), (190, 200, 205), np.uint8); cv2.rectangle(strip, (0, 0), (399, 59), (120, 120, 130), 3)
sc = V.build_scene(root, fake, df, 25.75, 12, 0, (0, 1), strips=[strip] * 4, floor_bgr=floor)
vd = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "components", "viewer3d")
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=vd)
srv = socketserver.TCPServer(("127.0.0.1", 0), h); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
out = sys.argv[1] if len(sys.argv) > 1 else "viewer_test.png"
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": 900, "height": 600})
    logs = []; pg.on("console", lambda m: logs.append(m.text)); pg.on("pageerror", lambda e: logs.append("PAGEERR " + str(e)))
    pg.goto(f"http://127.0.0.1:{port}/index.html")
    pg.evaluate("s => window.postMessage({type:'streamlit:render', args:{scene_id:'t', height:600, scene:s}}, '*')", sc)
    pg.wait_for_function("window.__ready && window.__ready()", timeout=15000)
    pg.wait_for_timeout(2500)
    pg.screenshot(path=out)
    print("logs:", logs[:8]); b.close()
