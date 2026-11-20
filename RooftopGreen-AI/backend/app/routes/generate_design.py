import base64
import datetime
import io
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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

from app.services.garden_render import render_garden, RenderError, PROMPT_VERSION

router = APIRouter(prefix="", tags=["generate-design"])


def get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        return key
    env_paths = [
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent.parent / ".env",
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


def extract_clean_plant_names(selected_plants: Optional[List[Any]]) -> List[str]:
    clean = []
    if not selected_plants:
        return clean
    for p in selected_plants:
        if isinstance(p, dict):
            name = p.get("name_en") or p.get("name") or p.get("crop") or ""
        elif isinstance(p, str):
            name = p
        else:
            continue
        no_bn = re.sub(r'\([^\)]*[\u0980-\u09FF][^\)]*\)', '', name).strip()
        base_name = no_bn or name.split('(')[0].strip()
        if base_name and base_name not in clean:
            clean.append(base_name)
    return clean


class GenerateDesignPayload(BaseModel):
    view_id: Optional[str] = Field(default=None, description="e.g. view_1, view_2, view_3, view_4")
    view: Optional[str] = Field(default=None)
    view_index: Optional[int] = Field(default=None)
    angle: Optional[str] = Field(default=None)
    image_base64: Optional[str] = Field(default=None)
    image_url: Optional[str] = Field(default=None)
    boundary_pins: Optional[List[Any]] = Field(default_factory=list)
    grid_cells: Optional[Dict[str, Any]] = Field(default_factory=dict)
    variant: Optional[str] = Field(default="Balanced")
    selected_plants: Optional[List[Any]] = Field(default_factory=list)
    lighting: Optional[str] = Field(default="daylight")
    width_ft: Optional[float] = Field(default=20.0)
    depth_ft: Optional[float] = Field(default=15.0)
    session_id: Optional[str] = Field(default=None)
    zones: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    regenerate_nonce: Optional[str] = Field(default=None)
    client_fingerprint: Optional[str] = Field(default=None)
    image_width: Optional[int] = Field(default=None)
    image_height: Optional[int] = Field(default=None)
    pins_space: Optional[str] = Field(default=None)


@router.post("/generate-design")
def generate_design(payload: Optional[GenerateDesignPayload] = None):
    if payload is None:
        payload = GenerateDesignPayload()

    # Rule: no image_base64 -> HTTP 400. Never guess or use stock photos.
    if not payload.image_base64:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error_code": "NO_IMAGE",
                "detail": "No rooftop photo provided. Please upload a photo for this view in Step 2.",
            },
        )

    raw_b64 = payload.image_base64
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(raw_b64)
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error_code": "INVALID_IMAGE",
                "detail": f"Failed to decode image data: {e}",
            },
        )

    clean_plants = extract_clean_plant_names(payload.selected_plants)
    zones = payload.zones or []

    try:
        result = render_garden(
            image_bytes=image_bytes,
            pins_norm=payload.boundary_pins,
            plants=clean_plants,
            variant=payload.variant or "Balanced",
            lighting=payload.lighting or "daylight",
            zones=zones,
            nonce=payload.regenerate_nonce,
        )
    except RenderError as e:
        return JSONResponse(
            status_code=e.http,
            content={
                "status": "error",
                "error_code": e.code,
                "detail": e.message,
            },
        )
    except Exception as exc:
        print(f"[generate_design] Unexpected rendering error: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "detail": str(exc),
            },
        )

    meta = result.get("meta", {})
    jpeg_bytes = result["jpeg"]
    b64_output = base64.b64encode(jpeg_bytes).decode("utf-8")
    data_uri = f"data:image/jpeg;base64,{b64_output}"

    # Log one summary line
    pins_used = meta.get("pins_used", 0)
    sent_size = f"{len(image_bytes)}b"
    ai_size = meta.get("ai_size", [])
    aspect_err = meta.get("aspect_error", 0.0)
    matte_cov = meta.get("matte_coverage", 0.0)
    comp_kept = meta.get("components_kept", 0)
    comp_rej = meta.get("components_rejected", 0)
    comp_mode = meta.get("composite_mode", "unknown")
    seed = result.get("seed")
    elapsed = result.get("elapsed")
    print(
        f"[generate_design] pins={pins_used} sent_size={sent_size} ai_size={ai_size} "
        f"aspect_err={aspect_err} matte_cov={matte_cov} comp_kept={comp_kept} "
        f"comp_rej={comp_rej} mode={comp_mode} seed={seed} elapsed={elapsed}s"
    )

    response_data = {
        # Compatibility keys
        "status": "ok",
        "image_url": data_uri,
        "preview_data_url": data_uri,
        "view_name": "replicate_flux_kontext.jpg",
        "source": "replicate_flux_kontext",
        "gemini_prompt": result["prompt"],
        # Extended keys
        "prompt_used": result["prompt"],
        "seed": seed,
        "request_id": result["request_id"],
        "prompt_version": result["prompt_version"],
        "composite_mode": comp_mode,
        "width": meta.get("width"),
        "height": meta.get("height"),
        "matte": meta,
        "client_fingerprint": payload.client_fingerprint,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    return JSONResponse(
        content=response_data,
        headers={"Cache-Control": "no-store"},
    )
