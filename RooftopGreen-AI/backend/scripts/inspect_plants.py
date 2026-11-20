import csv
import json
from pathlib import Path

csv_path = Path("backend/data/plants.csv")
json_path = Path("backend/data/research/verified_plants.json")

with open(csv_path, "r", encoding="utf-8") as f:
    csv_plants = list(csv.DictReader(f))

with open(json_path, "r", encoding="utf-8") as f:
    v_plants = json.load(f)

csv_map = {p["id"]: p for p in csv_plants}
print(f"Total CSV plants: {len(csv_plants)}")
print(f"Total Verified plants: {len(v_plants)}")

# Direct explicit dictionary mapping for research plants
# P001 to P030
EXPLICIT_MAP = {
    "P001": "red_amaranth",      # Red Amaranth (lal shak)
    "P002": "spinach",           # Spinach (palong shak)
    "P003": "malabar_spinach",   # Malabar spinach (pui shak)
    "P004": "coriander",         # Coriander (dhone pata)
    "P005": "lettuce",           # Lettuce (needs new entry if missing)
    "P006": "mint",              # Mint (pudina)
    "P007": "tomato",            # Tomato
    "P008": "brinjal",           # Brinjal (begun)
    "P009": "chili",             # Chili
    "P010": "okra",              # Okra (dherosh / Lady's Finger)
    "P011": "cucumber",          # Cucumber (shosha)
    "P012": "capsicum",          # Capsicum
    "P013": "bottle_gourd",      # Bottle gourd (lau)
    "P014": "bitter_gourd",      # Bitter gourd (korola)
    "P015": "hyacinth_bean",     # Hyacinth Bean (sheem - check if exists)
    "P016": "ridge_gourd",       # Ridge gourd (jhinga)
    "P017": "kagzi_lemon",       # Lemon (kagzi lemon - check)
    "P018": "guava",             # Guava (peyara)
    "P019": "pomegranate",       # Pomegranate (dalim)
    "P020": "strawberry",        # Strawberry
    "P021": "marigold",          # Marigold (gada)
    "P022": "rose",              # Rose (check)
    "P023": "hibiscus",          # Hibiscus (jaba)
    "P024": "jasmine_beli",      # Arabian Jasmine (beli)
    "P025": "basil",             # Holy Basil (tulsi)
    "P026": "aloe",              # Aloe vera
    "P027": "thankuni",          # Indian Pennywort (thankuni)
    "P028": "curry_leaf",        # Curry leaf (kari pata)
    "P029": "radish",            # Radish (mula)
    "P030": "fenugreek",         # Fenugreek (methi - check if exists)
}

for vp in v_plants:
    pid = vp["plant_id"]
    target_id = EXPLICIT_MAP.get(pid)
    match = csv_map.get(target_id)
    if match:
        print(f"EXACT: {pid} '{vp['plant_name']}' -> '{target_id}' ({match['name_en']})")
    else:
        # Search all CSV plants for close names
        candidates = [p["id"] for p in csv_plants if vp["plant_name"].lower() in p["name_en"].lower() or vp["plant_name"].lower() in p["id"]]
        print(f"MISSING or DIFFERENT ID: {pid} '{vp['plant_name']}' -> mapped '{target_id}', candidates: {candidates}")
