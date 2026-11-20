"""Wrapper for the browser painter component (components/painter/index.html)."""
import base64
import os
import cv2
import streamlit.components.v1 as components

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "components", "painter")
_component = components.declare_component("garden_painter", path=_PATH)


def data_url(bgr, quality=88):
    ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def painter(image_url, image_id, info, grid_ft, tool, radius_ft, color_rgb, label, key):
    """Returns None or a dict {nonce, tool, radius_ft, points} when the user finishes a shape."""
    return _component(image=image_url, image_id=image_id, info=info, grid_ft=grid_ft, tool=tool,
                      radius_ft=radius_ft, color=list(color_rgb), label=label, key=key, default=None)
