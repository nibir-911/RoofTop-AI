import math
import os
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project
from app.schemas import (
    RoofAreaIn, RoofAreaResponse,
    RoofGridIn, RoofGridResponse,
    CellConditionsIn, ObstaclesIn
)

router = APIRouter(prefix="/roof", tags=["roof"])

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def calculate_polygon_area(corners: List[List[float]]) -> float:
    n = len(corners)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += corners[i][0] * corners[j][1]
        area -= corners[j][0] * corners[i][1]
    return abs(area) / 2.0


@router.post("/upload")
async def upload_roof_photo(edge_id: str = Form(""), file: UploadFile = File(...)):
    filename = f"{edge_id}_{file.filename}" if edge_id else file.filename
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return {
        "status": "ok",
        "edge_id": edge_id,
        "filename": filename,
        "url": f"/static/uploads/{filename}"
    }


@router.post("/analyze")
async def analyze_roof(data: Dict[str, Any]):
    return {
        "status": "ok",
        "detected_type": "flat_rooftop",
        "confidence": 0.92,
        "estimated_sqft": 350.0,
        "detected_obstacles": [
            {"id": "obs_water_tank", "label": "Water Tank", "cells": ["A1"], "width_ft": 4.0, "depth_ft": 4.0}
        ],
        "solar_access": "excellent"
    }


@router.post("/area", response_model=RoofAreaResponse)
def calculate_area(data: RoofAreaIn):
    corners = data.corners
    raw_area = calculate_polygon_area(corners)
    unit = data.unit.lower() if data.unit else "ft"

    if unit in ["m", "meter", "meters"]:
        area_m2 = raw_area
        area_sqft = raw_area * 10.7639
        corners_ft = [[p[0] * 3.28084, p[1] * 3.28084] for p in corners]
    else:
        area_sqft = raw_area
        area_m2 = raw_area / 10.7639
        corners_ft = corners

    is_valid = len(corners) >= 3 and area_sqft > 10.0
    return {
        "corners_ft": corners_ft,
        "area_sqft": round(area_sqft, 2),
        "area_m2": round(area_m2, 2),
        "is_valid": is_valid,
        "note": "Area computed via planar polygon projection."
    }


@router.post("/grid", response_model=RoofGridResponse)
def generate_grid(data: RoofGridIn, db: Session = Depends(get_db)):
    grid_ft = data.grid_ft or 2.0
    width_ft = max(data.width_ft, 4.0)
    depth_ft = max(data.depth_ft, 4.0)
    cols = math.ceil(width_ft / grid_ft)
    rows = math.ceil(depth_ft / grid_ft)

    cells = {}
    for r in range(rows):
        for c in range(cols):
            col_letter = chr(65 + (c % 26)) if c < 26 else f"A{chr(65 + (c % 26))}"
            cell_id = f"{col_letter}{r + 1}"
            x0 = c * grid_ft
            y0 = r * grid_ft
            x1 = min((c + 1) * grid_ft, width_ft)
            y1 = min((r + 1) * grid_ft, depth_ft)
            area = (x1 - x0) * (y1 - y0)
            
            sunlight = "FULL_SUN"
            if r == 0:
                sunlight = "MORNING_SUN"
            elif r == rows - 1:
                sunlight = "AFTERNOON_SUN"

            cells[cell_id] = {
                "id": cell_id,
                "row": r,
                "col": c,
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1,
                "area_sqft": area,
                "clipped_area_sqft": area,
                "sunlight": sunlight,
                "zone": "GARDENING"
            }

    project = db.query(Project).filter(Project.session_id == data.session_id).first()
    if project:
        roof_data = project.roof_data or {}
        roof_data.update({
            "width_ft": width_ft,
            "depth_ft": depth_ft,
            "grid_ft": grid_ft,
            "bearing": data.bearing
        })
        project.roof_data = roof_data
        project.cells = cells
        db.commit()

    return {
        "session_id": data.session_id,
        "rows": rows,
        "cols": cols,
        "grid_ft": grid_ft,
        "cells": cells
    }


@router.post("/cells/conditions")
def save_cell_conditions(data: CellConditionsIn, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.session_id == data.session_id).first()
    if project:
        current_cells = project.cells or {}
        for cid, cond in data.cells.items():
            if cid in current_cells:
                if cond.sunlight:
                    current_cells[cid]["sunlight"] = cond.sunlight
                if cond.zone:
                    current_cells[cid]["zone"] = cond.zone
            else:
                current_cells[cid] = cond.dict()
        project.cells = current_cells
        db.commit()
    return {"status": "ok", "updated_cells": len(data.cells)}


@router.post("/obstacles")
def save_obstacles(data: ObstaclesIn, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.session_id == data.session_id).first()
    if project:
        roof_data = project.roof_data or {}
        roof_data["obstacles"] = [o.dict() for o in data.obstacles]
        project.roof_data = roof_data
        
        # update blocked cells
        current_cells = project.cells or {}
        for obs in data.obstacles:
            for cid in obs.cells:
                if cid in current_cells:
                    current_cells[cid]["zone"] = "BLOCKED"
        project.cells = current_cells
        db.commit()
    return {"status": "ok", "obstacles_count": len(data.obstacles)}
