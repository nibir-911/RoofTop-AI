"""
Roof Detect Route: AI-powered Automatic Roof Perimeter & Obstacle Detection
Uses Gemini Vision to detect:
1. Flat walkable rooftop floor perimeter points (normalized 0.0 to 1.0).
2. Obstacles, water tanks, pillars, or clutter on the floor surface.
Includes calibrated geometric fallback polygon for resilience.
"""
import os
import re
import json
import base64
import io
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from PIL import Image
from app.schemas import RoofDetectIn, RoofDetectResponse, NormalizedPoint, DetectedObstacle

# Google GenAI SDK import
try:
    from google import genai
except ImportError:
    genai = None

# python-dotenv loading
try:
    from dotenv import load_dotenv
    env_candidate = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_candidate.exists():
        load_dotenv(dotenv_path=env_candidate)
    else:
        load_dotenv()
except ImportError:
    pass

router = APIRouter(tags=["roof-detection"])

DEFAULT_FALLBACK_PERIMETER = [
    {"x": 0.18, "y": 0.55},
    {"x": 0.85, "y": 0.55},
    {"x": 0.92, "y": 0.92},
    {"x": 0.12, "y": 0.92}
]

def get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        return key
    env_paths = [
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path(".env"),
    ]
    for ep in env_paths:
        if ep.exists():
            try:
                with open(ep, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY="):
                            val = line.split("GEMINI_API_KEY=", 1)[1].strip().strip("'\"")
                            if val:
                                return val
            except Exception:
                pass
    return ""


@router.post("/detect-roof", response_model=RoofDetectResponse)
@router.post("/detect-roof-grid", response_model=RoofDetectResponse)
def detect_roof_grid(payload: RoofDetectIn):
    """
    Analyzes an uploaded rooftop photo using Gemini Vision to automatically outline
    the flat concrete floor boundary and identify floor obstacles.
    """
    raw_b64 = payload.image_base64
    if not raw_b64:
        return RoofDetectResponse(
            status="fallback",
            perimeter_points=[NormalizedPoint(**p) for p in DEFAULT_FALLBACK_PERIMETER],
            obstacles=[],
            message="No image provided, using default calibrated polygon."
        )

    # 1. Decode & downsample image if necessary
    pil_image = None
    try:
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(raw_b64)
        pil_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        max_dim = 1024
        w, h = pil_image.size
        if w > max_dim or h > max_dim:
            if w > h:
                new_w = max_dim
                new_h = int((h * max_dim) / w)
            else:
                new_h = max_dim
                new_w = int((w * max_dim) / h)
            pil_image = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    except Exception as img_err:
        print(f"[roof_detect] Image decode error: {img_err}")
        return RoofDetectResponse(
            status="fallback",
            perimeter_points=[NormalizedPoint(**p) for p in DEFAULT_FALLBACK_PERIMETER],
            obstacles=[],
            message="Failed to decode image, using default calibrated polygon."
        )

    # 2. Setup Gemini Client
    api_key = get_gemini_api_key()
    client = None
    if genai and api_key:
        try:
            client = genai.Client(api_key=api_key)
        except Exception as client_err:
            print(f"[roof_detect] GenAI client init error: {client_err}")

    if not client or not pil_image:
        return RoofDetectResponse(
            status="fallback",
            perimeter_points=[NormalizedPoint(**p) for p in DEFAULT_FALLBACK_PERIMETER],
            obstacles=[],
            message="Gemini client unavailable, using default calibrated polygon."
        )

    # 3. Vision Prompt
    vision_prompt = (
        "You are an expert AI Architectural & Computer Vision Model analyzing rooftop photos for rooftop gardening installation.\n"
        "Visually inspect this rooftop photograph and detect:\n"
        "1. The perimeter boundary outlining ONLY the flat, walkable concrete rooftop floor surface.\n"
        "   STRICT RULES:\n"
        "   - Outline ONLY the walkable floor where plant containers, planters, and walkways can physically sit.\n"
        "   - Strictly exclude the open sky, neighboring buildings, parapet wall tops, and outer ledges.\n"
        "   - Provide 4 to 6 normalized coordinates in sequential order around the floor perimeter (e.g., top-left of floor, top-right of floor, bottom-right, bottom-left).\n"
        "2. Any obstacles, water tanks, air conditioning units, solar frame bases, or clutter sitting on the floor surface.\n\n"
        "Respond STRICTLY with a single JSON object (no markdown backticks, no comments, no additional text):\n"
        "{\n"
        '  "perimeter_points": [\n'
        '    {"x": 0.18, "y": 0.55},\n'
        '    {"x": 0.85, "y": 0.55},\n'
        '    {"x": 0.92, "y": 0.92},\n'
        '    {"x": 0.12, "y": 0.92}\n'
        '  ],\n'
        '  "obstacles": [\n'
        '    {"label": "water_tank", "x": 0.35, "y": 0.60, "width": 0.12, "height": 0.15}\n'
        '  ]\n'
        "}\n"
        "All coordinates and dimensions must be normalized floats between 0.0 and 1.0 (where 0.0,0.0 is top-left of the image and 1.0,1.0 is bottom-right)."
    )

    candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[pil_image, vision_prompt],
                )
                if response and response.text:
                    raw_text = response.text.strip()
                    if raw_text.startswith("```"):
                        raw_text = re.sub(r"^```(?:json)?", "", raw_text, flags=re.IGNORECASE).strip()
                        raw_text = re.sub(r"```$", "", raw_text).strip()

                    parsed = json.loads(raw_text)
                    raw_pts = parsed.get("perimeter_points", [])
                    raw_obstacles = parsed.get("obstacles", [])

                    if isinstance(raw_pts, list) and len(raw_pts) >= 3:
                        valid_pts = []
                        for pt in raw_pts:
                            if isinstance(pt, dict) and "x" in pt and "y" in pt:
                                px = max(0.0, min(1.0, float(pt["x"])))
                                py = max(0.0, min(1.0, float(pt["y"])))
                                valid_pts.append(NormalizedPoint(x=px, y=py))

                        valid_obs = []
                        for obs in raw_obstacles:
                            if isinstance(obs, dict) and "x" in obs and "y" in obs:
                                ox = max(0.0, min(1.0, float(obs["x"])))
                                oy = max(0.0, min(1.0, float(obs["y"])))
                                ow = max(0.01, min(1.0, float(obs.get("width", 0.1))))
                                oh = max(0.01, min(1.0, float(obs.get("height", 0.1))))
                                lbl = str(obs.get("label", "Obstacle"))
                                valid_obs.append(DetectedObstacle(label=lbl, x=ox, y=oy, width=ow, height=oh))

                        if len(valid_pts) >= 3:
                            print(f"[roof_detect] Gemini Vision ({model_name}) successfully detected {len(valid_pts)} perimeter points and {len(valid_obs)} obstacles.")
                            return RoofDetectResponse(
                                status="ok",
                                perimeter_points=valid_pts,
                                obstacles=valid_obs,
                                message="Rooftop floor perimeter and obstacles detected by Gemini Vision.",
                                model=model_name
                            )
            except Exception as e:
                print(f"[roof_detect] Attempt {attempt+1} with {model_name} note: {e}")

    # Fallback if models are unavailable, rate-limited, or failed to parse
    print("[roof_detect] Using fallback calibrated rooftop perspective polygon.")
    return RoofDetectResponse(
        status="fallback",
        perimeter_points=[NormalizedPoint(**p) for p in DEFAULT_FALLBACK_PERIMETER],
        obstacles=[],
        message="Using calibrated rooftop perspective polygon."
    )
