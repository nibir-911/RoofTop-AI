from typing import List, Optional
from fastapi import APIRouter, HTTPException
from app.routes.garden import load_plants_data
from app.schemas import PlantOut

router = APIRouter(tags=["plants"])

@router.get("/plants", response_model=List[PlantOut])
def get_plants():
    return load_plants_data()

@router.get("/guides/{plant_id}")
def get_guide(plant_id: str):
    plants = load_plants_data()
    plant = next((p for p in plants if p["id"].lower() == plant_id.lower()), None)
    if not plant:
        # Fallback generic plant info
        plant = {
            "id": plant_id,
            "name_en": plant_id.replace("_", " ").title(),
            "name_bn": "",
            "category": "vegetable",
            "form": "bush",
            "sun_min": 5.0,
            "sun_max": 8.0,
            "water": "med",
            "maint": "med",
            "cost_bdt": 35.0,
            "is_verified": False,
        }

    container_rec = (
        f"Container: {plant.get('pot_diameter_inch', '10-14 inch')} diameter ({plant.get('pot_depth_inch', '10-14 inch')} depth), spacing {plant.get('spacing_inch', '6-12 inch')} with adequate drainage."
        if plant.get("pot_depth_inch")
        else "Minimum 10-14 inch depth planter or 15L geobag with adequate drainage holes."
    )

    harvest_note = (
        f"Growth duration: {plant.get('growth_duration_days')}. Harvest in early morning for peak nutrition and flavor."
        if plant.get("growth_duration_days")
        else "Harvest outer leaves or ripe fruit regularly in the morning to encourage vigorous continuing growth."
    )

    return {
        "plant": plant,
        "care_guide": {
            "title": f"Growing {plant['name_en']} on Bangladesh Rooftops",
            "scientific_name": plant.get("scientific_name"),
            "rooftop_suitability": plant.get("rooftop_suitability", "Suitable"),
            "sunlight_req": f"Requires {plant.get('sun_min', 4)} to {plant.get('sun_max', 8)} hours of direct sunshine daily.",
            "watering_schedule": f"Watering level: {str(plant.get('water', 'med')).upper()}. In summer/chaitra heat, water twice daily early morning and late afternoon.",
            "soil_and_fertilizer": "Use a 50:30:20 mix of loamy soil, well-rotted cow dung/vermicompost, and coco peat for weight reduction.",
            "container_recommendation": container_rec,
            "pest_prevention": "Spray organic neem oil solution (5ml/L water with a drop of liquid soap) every 10 days to deter aphids and mealybugs.",
            "harvest_tips": harvest_note,
            "source_title": plant.get("source_title"),
            "source_page": plant.get("source_page"),
            "source_url": plant.get("source_url"),
            "is_verified": plant.get("is_verified", False),
        },
        "seasonal_calendar": [
            {"season": "Winter (Rabi: Nov-Feb)", "action": "Peak growing season. Provide full sun and weekly vermicompost top-dressing."},
            {"season": "Summer (Kharif-1: Mar-May)", "action": "Mulch root zone with straw or coco husk to conserve moisture from harsh sun."},
            {"season": "Monsoon (Kharif-2: Jun-Oct)", "action": "Ensure drainage holes are unobstructed to prevent waterlogging and root rot."}
        ]
    }
