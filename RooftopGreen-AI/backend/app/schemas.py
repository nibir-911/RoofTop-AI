"""Pydantic v2 schemas for RooftopGreen AI API."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import datetime


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

class MixPreferences(BaseModel):
    vegetable: float = 0.3
    flower: float = 0.2
    fruit: float = 0.2
    herb: float = 0.2
    ornamental: float = 0.1


class PreferencesIn(BaseModel):
    budget_bdt: Optional[float] = Field(default=20000.0, description="Total budget in BDT")
    effort: Optional[str] = Field(default="weekends", description="daily | weekends | managed")
    harvest: Optional[str] = Field(default="home", description="home | sell | decor")
    kids_pets: Optional[bool] = Field(default=False, description="Avoid hazardous plants")
    allow_wall: Optional[bool] = Field(default=True, description="Allow climbers/hanging plants")
    allow_trees: Optional[bool] = Field(default=True, description="Allow shrubs/small trees")
    load_limit_kg_m2: Optional[float] = Field(default=150.0, description="Structural load limit kg/m²")
    mix: Optional[MixPreferences] = Field(default_factory=MixPreferences)
    month: Optional[int] = Field(default=None, ge=1, le=12, description="Planning month (1-12); defaults to current")
    bearing: Optional[float] = Field(default=0.0, description="Roof bearing/orientation in degrees")
    location: Optional[str] = Field(default="Dhaka, Bangladesh")


# ---------------------------------------------------------------------------
# Roof
# ---------------------------------------------------------------------------

class RoofAreaIn(BaseModel):
    corners: List[List[float]] = Field(..., description="List of [x, y] corner points")
    unit: Optional[str] = Field(default="ft", description="ft | m")
    diagonal: Optional[float] = Field(default=None)


class RoofGridIn(BaseModel):
    session_id: str
    width_ft: float
    depth_ft: float
    grid_ft: Optional[float] = Field(default=2.0)
    bearing: Optional[float] = Field(default=0.0)


class CellConditions(BaseModel):
    sunlight: Optional[str] = Field(default="FULL_SUN",
                                    description="FULL_SUN | MORNING_SUN | AFTERNOON_SUN | SHADE")
    zone: Optional[str] = Field(default="GARDENING",
                                description="GARDENING | WALKWAY | BLOCKED")


class CellConditionsIn(BaseModel):
    session_id: str
    cells: Dict[str, CellConditions]


class ObstacleItem(BaseModel):
    id: str
    label: str
    cells: List[str]
    width_ft: Optional[float] = None
    depth_ft: Optional[float] = None


class ObstaclesIn(BaseModel):
    session_id: str
    obstacles: List[ObstacleItem]


# ---------------------------------------------------------------------------
# Garden
# ---------------------------------------------------------------------------

class GardenRecommendIn(BaseModel):
    session_id: str
    month: Optional[int] = Field(default=None, ge=1, le=12)


class GardenLayoutIn(BaseModel):
    session_id: str
    month: Optional[int] = Field(default=None, ge=1, le=12)
    variant: Optional[str] = Field(default=None, description="Productive | Colorful | Balanced; None = all 3")
    seed: Optional[int] = Field(default=0)


class GardenMaterialsIn(BaseModel):
    session_id: str
    variant: Optional[str] = Field(default="Productive")
    plant_count: Optional[int] = None
    roof_area_sqft: Optional[float] = None
    budget_bdt: Optional[float] = None
    budget: Optional[float] = None


class GardenExplainIn(BaseModel):
    session_id: Optional[str] = Field(default="default_session")
    variant: Optional[str] = Field(default="Productive")
    selected_plants: Optional[List[str]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Plant Doctor
# ---------------------------------------------------------------------------

class PlantDoctorIn(BaseModel):
    symptoms: List[str] = Field(..., description="List of symptom strings")
    follow_up_answers: Optional[Dict[str, str]] = Field(default_factory=dict)
    image_base64: Optional[str] = Field(default=None, description="Optional base64 encoded image")

# Alias for backward-compatibility
PlantDoctorRequest = PlantDoctorIn


class PlantDoctorChatIn(BaseModel):
    message: str
    query: Optional[str] = None
    diagnosis_context: Optional[Dict[str, Any]] = None
    chat_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    last_diagnosis: Optional[str] = None


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class OrderItemIn(BaseModel):
    product_id: str
    name: str
    qty: int
    unit_price_bdt: float


class OrderIn(BaseModel):
    project_id: Optional[str] = None
    items: List[OrderItemIn]
    payment_method: Optional[str] = Field(default="cod", description="cod | sandbox")


class WebhookIn(BaseModel):
    sandbox_token: str
    event: Optional[str] = Field(default="payment_success")


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    app: str


class PreferencesResponse(BaseModel):
    session_id: str
    project_id: str
    status: str


class RoofAreaResponse(BaseModel):
    corners_ft: List[List[float]]
    area_sqft: float
    area_m2: float
    is_valid: bool
    note: Optional[str] = None


class GridCell(BaseModel):
    id: str
    row: int
    col: int
    x0: float
    y0: float
    x1: float
    y1: float
    area_sqft: float
    clipped_area_sqft: float
    sunlight: str
    zone: str


class RoofGridResponse(BaseModel):
    session_id: str
    rows: int
    cols: int
    grid_ft: float
    cells: Dict[str, Any]


class PlantOut(BaseModel):
    id: str
    name_en: str
    name_bn: Optional[str] = None
    scientific_name: Optional[str] = None
    category: str
    form: str
    score: Optional[float] = None
    why: Optional[str] = None
    sun_min: float
    sun_max: float
    height_ft: float
    canopy_ft: float
    bloom_hex: Optional[str] = None
    verified: bool
    is_verified: Optional[bool] = False
    cost_bdt: float
    maint: str
    water: str
    rooftop_suitability: Optional[str] = None
    source_title: Optional[str] = None
    source_page: Optional[str] = None
    source_url: Optional[str] = None
    pot_diameter_inch: Optional[str] = None
    pot_depth_inch: Optional[str] = None
    spacing_inch: Optional[str] = None
    growth_duration_days: Optional[str] = None
    harvest_days: Optional[str] = None
    wet_weight_kg: Optional[float] = None
    notes: Optional[str] = None


class PlacementOut(BaseModel):
    row: int
    col: int
    plant_id: str
    name: str
    category: str
    form: str
    zone: str


class LayoutVariantOut(BaseModel):
    variant: str
    placements: List[PlacementOut]
    notes: List[str]
    scene_json: Dict[str, Any]
    bom_summary: Dict[str, Any]


class BOMItem(BaseModel):
    name: str
    qty: float
    unit: str
    unit_cost_bdt: float
    total_bdt: float


class MaterialsResponse(BaseModel):
    items: List[BOMItem]
    subtotal_bdt: float
    labour_bdt: float
    total_bdt: float
    budget_bdt: Optional[float] = None
    structural_load: Dict[str, Any]


class SupplierOut(BaseModel):
    id: str
    name: str
    category: Optional[str] = "Gardening Store"
    area: Optional[str] = "Dhaka, Bangladesh"
    contact: Optional[str] = ""
    verified: Optional[bool] = True
    website_or_page: Optional[str] = None
    supplier_type: Optional[str] = None
    product_categories: Optional[str] = None
    seller_status: Optional[str] = None
    source_url: Optional[str] = None
    notes: Optional[str] = None


class ProductOut(BaseModel):
    id: str
    name: str
    supplier_id: Optional[str] = None
    category: str
    unit: Optional[str] = "piece"
    price_bdt: float
    in_stock: Optional[bool] = True
    size_or_dimension: Optional[str] = None
    package_quantity: Optional[str] = None
    wet_weight_kg: Optional[float] = None
    seller_name: Optional[str] = None
    platform_name: Optional[str] = None
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    availability: Optional[str] = "Available"
    brand: Optional[str] = None
    regular_price_bdt: Optional[float] = None
    offer_price_bdt: Optional[float] = None


class OrderResponse(BaseModel):
    order_id: str
    status: str
    total_bdt: float
    sandbox_token: Optional[str] = None


class PlantDoctorResponse(BaseModel):
    primary_cause: str
    confidence_pct: int
    confidence_label: str
    alternative_causes: List[str]
    follow_up_questions: List[str]
    care_steps: List[str]
    disclaimer: str
    severity: Optional[str] = "Moderate"
    organic_remedy: Optional[str] = None
    prevention: Optional[str] = None
    engine: Optional[str] = "rule_engine"


# ---------------------------------------------------------------------------
# Roof Detection (AI Perimeter & Obstacles)
# ---------------------------------------------------------------------------

class NormalizedPoint(BaseModel):
    x: float
    y: float


class DetectedObstacle(BaseModel):
    label: str = "Obstacle"
    x: float
    y: float
    width: float
    height: float


class RoofDetectIn(BaseModel):
    image_base64: Optional[str] = None
    view_id: Optional[str] = "view_1"


class RoofDetectResponse(BaseModel):
    status: str = "ok"
    perimeter_points: List[NormalizedPoint]
    obstacles: List[DetectedObstacle] = []
    message: Optional[str] = None
    model: Optional[str] = None


class RoofAnalysisResponse(BaseModel):
    status: str = "ok"
    estimated_area_sqft: float = 600.0
    sunlight_profile: str = "Full Sun"
    parapet_safety: str = "Verified"
    detected_features: List[str] = []
    message: Optional[str] = None
    model: Optional[str] = None

