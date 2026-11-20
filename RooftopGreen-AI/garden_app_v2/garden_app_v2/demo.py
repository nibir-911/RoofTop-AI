"""Built-in demo roof (synthetic, no real photos): 20 x 16 ft, 6th-floor block in corner C with outer stair + stair-house door."""
import cv2
import numpy as np

DEMO_L = [20.0, 16.0, 20.0, 16.0]
DEMO_ROOF = {"block": {"w": 8.0, "d": 8.0, "corner": "C"}, "diff_ft": 10.0, "floors": [5, 6],
             "openings": [{"kind": "outer_stair", "face": "S", "pos_ft": 4.0, "width_ft": 3.0},
                          {"kind": "door", "face": "W", "pos_ft": 4.0, "width_ft": 3.0}]}


def demo_strips(lengths, ppf, height_ft, seed=3):
    """Plain painted parapet with a simple metal railing pattern, one image per side."""
    rng = np.random.default_rng(seed)
    out = []
    for L in lengths:
        W, H = int(L * ppf), int(height_ft * ppf)
        img = np.full((H, W, 3), (200, 205, 208), np.uint8)
        img = np.clip(img.astype(int) + rng.integers(-6, 7, img.shape), 0, 255).astype(np.uint8)
        cv2.rectangle(img, (0, 0), (W - 1, int(H * 0.22)), (170, 175, 180), -1)          # coping
        for x in range(8, W, 18):
            cv2.line(img, (x, int(H * 0.25)), (x, H - 4), (110, 112, 118), 3, cv2.LINE_AA)  # balusters
        cv2.line(img, (0, int(H * 0.3)), (W, int(H * 0.3)), (90, 92, 98), 4, cv2.LINE_AA)
        cv2.line(img, (0, H - 6), (W, H - 6), (90, 92, 98), 4, cv2.LINE_AA)
        out.append(img)
    return out
