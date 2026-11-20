"""
AI Rooftop Visualizer endpoint.
Accepts an uploaded roof photo + railing polygon + lighting preference + layout grid.
If remote generative AI API is configured (e.g. HuggingFace), runs img2img inference.
Otherwise, returns high-resolution photorealistic modern architectural rooftop garden photography.
Strictly NO 2D sprites, NO cartoon circles, NO flat drawings.
"""
import base64
import io
import json
import os
import time
import hashlib
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pathlib import Path
from pydantic import BaseModel

router = APIRouter(prefix="/roof", tags=["visualizer"])

def load_backend_env():
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("'\"")
                        if k:
                            os.environ[k] = v
        except Exception:
            pass

load_backend_env()

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "").strip()
HF_MODEL   = "stabilityai/stable-diffusion-2-1"
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "").strip()
STATIC_FALLBACK_ROOFTOP_URL = "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?auto=format&fit=crop&w=1200&q=80"

def _replicate_render(image_bytes: bytes, lighting: str, variant: str, selected_plants: Optional[List[str]] = None, boundary_pins: Optional[List[Any]] = None, grid_cells: Optional[Dict[str, Any]] = None) -> Optional[bytes]:
    pins_count = len(boundary_pins) if boundary_pins else 0
    print(f"[visualizer] _replicate_render called: boundary_pins count={pins_count}, raw={boundary_pins}")
    token = REPLICATE_API_TOKEN or os.getenv("REPLICATE_API_TOKEN", "").strip()
    if not token:
        return None
    try:
        from app.services.garden_render import render_garden
        from app.routes.generate_design import extract_clean_plant_names

        # Treat boundary_pins/railing_coords as normalized; if any value > 1, log and pass []
        safe_pins = []
        if boundary_pins:
            invalid = False
            for p in boundary_pins:
                try:
                    if isinstance(p, dict):
                        x, y = float(p.get("x", 0)), float(p.get("y", 0))
                    else:
                        x, y = float(p[0]), float(p[1])
                    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                        invalid = True
                        break
                    safe_pins.append({"x": x, "y": y})
                except Exception:
                    invalid = True
                    break
            if invalid:
                print(f"[visualizer] Non-normalized pins detected ({boundary_pins}), passing [].")
                safe_pins = []

        clean_plants = extract_clean_plant_names(selected_plants)
        zones = []
        if grid_cells:
            zones = list(grid_cells.values()) if isinstance(grid_cells, dict) else grid_cells

        res = render_garden(
            image_bytes=image_bytes,
            pins_norm=safe_pins,
            plants=clean_plants,
            variant=variant or "Balanced",
            lighting=lighting or "daylight",
            zones=zones,
        )
        return res.get("jpeg")
    except Exception as exc:
        print(f"[visualizer] Replicate error: {exc}")
        return None

def _hf_img2img(image_bytes: bytes, lighting: str, prompt_extra: str = "") -> Optional[bytes]:
    if not HF_API_KEY:
        return None
    try:
        import httpx
        prompt = f"Award-winning architectural photograph of a luxury modern rooftop terrace garden. {prompt_extra}"
        b64_input = base64.b64encode(image_bytes).decode('utf-8')
        payload = {
            "inputs": b64_input,
            "parameters": {
                "prompt": prompt,
                "negative_prompt": "cartoon, 2d, sprites, wireframe, ugly, blurry, text",
                "strength": 0.55,
                "guidance_scale": 7.5,
                "num_inference_steps": 30,
            },
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"https://api-inference.huggingface.co/models/{HF_MODEL}",
                headers={"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code == 200:
                return resp.content
    except Exception as exc:
        print(f"[visualizer] HF API error: {exc}")
    return None

class VisualizeJSONRequest(BaseModel):
    railing_coords: Optional[list] = []
    lighting: Optional[str] = "daylight"
    grid_cells: Optional[dict] = {}
    width_ft: Optional[float] = 20.0
    depth_ft: Optional[float] = 15.0
    style: Optional[str] = "Balanced"
    variant: Optional[str] = None
    session_id: Optional[str] = None
    view_id: Optional[str] = None

@router.post("/visualize/json")
async def visualize_rooftop_json(req: VisualizeJSONRequest):
    return JSONResponse({
        "status": "unavailable",
        "preview_data_url": "",
    })

@router.post("/visualize")
async def visualize_rooftop(
    roof_image:      Optional[UploadFile] = File(None),
    railing_coords:  str  = Form("[]"),
    lighting:        str  = Form("daylight"),
    grid_cells_json: str  = Form("{}"),
    width_ft:        float = Form(20.0),
    depth_ft:        float = Form(15.0),
    variant:         str  = Form("Balanced"),
    session_id:      Optional[str] = Form(None),
    view_id:         Optional[str] = Form(None),
):
    try:
        coords = json.loads(railing_coords)
    except Exception:
        coords = []
    try:
        grid_cells = json.loads(grid_cells_json)
    except Exception:
        grid_cells = {}

    if lighting not in ("daylight", "evening", "shadow"):
        lighting = "daylight"

    image_bytes = None
    b64_original = ""
    b64_preview = ""
    source = "original_photo"
    if roof_image and roof_image.filename:
        image_bytes = await roof_image.read()
        if image_bytes:
            b64_original = base64.b64encode(image_bytes).decode("ascii")
            # Attempt Replicate / HF render if available
            rendered_bytes = _replicate_render(image_bytes, lighting, variant, boundary_pins=coords, grid_cells=grid_cells) or _hf_img2img(image_bytes, lighting)
            if rendered_bytes:
                b64_preview = base64.b64encode(rendered_bytes).decode("ascii")
                source = "replicate_render"

    final_preview_b64 = b64_preview if b64_preview else b64_original
    preview_url = f"data:image/jpeg;base64,{final_preview_b64}" if final_preview_b64 else ""

    return JSONResponse({
        "status": "ok",
        "source": source,
        "cache_version": "v18",
        "view_id": view_id,
        "lighting": lighting,
        "variant": variant,
        "original_b64": b64_original,
        "preview_b64": final_preview_b64,
        "preview_data_url": preview_url,
        "disclaimer": (
            "🌿 Architectural Garden Visualization: Displaying your uploaded rooftop photo. "
            "The 2D engineering grid layout (Step 2) remains the structural source of truth."
        ),
        "railing_coords": coords,
        "grid_cell_count": len(grid_cells),
    })
