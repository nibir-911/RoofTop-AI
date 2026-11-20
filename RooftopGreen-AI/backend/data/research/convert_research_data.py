import json
import re
from pathlib import Path
import pandas as pd
import numpy as np

def clean_val(v):
    if pd.isna(v) or v is None:
        return None
    if isinstance(v, (np.floating, float)) and np.isnan(v):
        return None
    if isinstance(v, (np.integer, int)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return round(float(v), 2)
    s = str(v).strip()
    return s if s != "" else None

def convert_excel_to_json():
    research_dir = Path(__file__).resolve().parent
    plant_file = research_dir / "01_Plant_Dataset_Cleaned.xlsx"
    product_supplier_file = research_dir / "02_Product_Supplier_Dataset_Cleaned.xlsx"

    print(f"Reading {plant_file}...")
    df_plants = pd.read_excel(plant_file, sheet_name="Plant_Dataset")
    df_plant_sources = pd.read_excel(plant_file, sheet_name="Source_Log")

    # Map sources by plant_id
    plant_sources_map = {}
    for _, row in df_plant_sources.iterrows():
        pid = clean_val(row.get("plant_id"))
        if pid:
            plant_sources_map[pid] = {
                "source_id": clean_val(row.get("source_id")),
                "source_title": clean_val(row.get("source_title")),
                "source_url": clean_val(row.get("source_url")),
                "page_section": clean_val(row.get("page/section")),
                "access_date": clean_val(row.get("access_date")),
                "fields_supported": clean_val(row.get("fields_supported")),
                "reliability_note": clean_val(row.get("reliability_note")),
            }

    plants_json = []
    for _, row in df_plants.iterrows():
        pid = clean_val(row.get("plant_id"))
        p_item = {
            "plant_id": pid,
            "plant_name": clean_val(row.get("plant_name")),
            "bangla_name": clean_val(row.get("bangla_name")),
            "scientific_name": clean_val(row.get("scientific_name")),
            "category": clean_val(row.get("category")),
            "rooftop_suitability": clean_val(row.get("rooftop_suitability")),
            "season": clean_val(row.get("season")),
            "sunlight": clean_val(row.get("sunlight")),
            "sunlight_hours": clean_val(row.get("sunlight_hours")),
            "water_need": clean_val(row.get("water_need")),
            "pot_diameter_inch": clean_val(row.get("pot_diameter_inch")),
            "pot_depth_inch": clean_val(row.get("pot_depth_inch")),
            "pot_volume_litre": clean_val(row.get("pot_volume_litre")),
            "spacing_inch": clean_val(row.get("spacing_inch")),
            "maintenance": clean_val(row.get("maintenance")),
            "growth_duration_days": clean_val(row.get("growth_duration_days")),
            "source_url": clean_val(row.get("source_url")),
            "source_title": clean_val(row.get("source_title")),
            "source_page": clean_val(row.get("source_page")),
            "source_type": clean_val(row.get("source_type")),
            "collected_date": clean_val(row.get("collected_date")),
            "verification_status": clean_val(row.get("verification_status")),
            "notes": clean_val(row.get("notes")),
            "source_log": plant_sources_map.get(pid),
        }
        plants_json.append(p_item)

    out_plants = research_dir / "verified_plants.json"
    with open(out_plants, "w", encoding="utf-8") as f:
        json.dump(plants_json, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(plants_json)} plants to {out_plants}")

    # -------------------------------------------------------------
    # 2. Products and Suppliers
    # -------------------------------------------------------------
    print(f"Reading {product_supplier_file}...")
    df_products = pd.read_excel(product_supplier_file, sheet_name="Product_Dataset")
    df_suppliers = pd.read_excel(product_supplier_file, sheet_name="Supplier_Dataset")
    df_prod_sources = pd.read_excel(product_supplier_file, sheet_name="Source_Log")

    prod_sources_map = {}
    for _, row in df_prod_sources.iterrows():
        prid = clean_val(row.get("product_id"))
        if prid:
            prod_sources_map[prid] = {
                "source_id": clean_val(row.get("source_id")),
                "source_title": clean_val(row.get("source_title")),
                "source_url": clean_val(row.get("source_url")),
                "seller": clean_val(row.get("seller")),
                "access_date": clean_val(row.get("access_date")),
                "information_supported": clean_val(row.get("information_supported")),
                "notes": clean_val(row.get("notes")),
            }

    products_json = []
    for _, row in df_products.iterrows():
        prid = clean_val(row.get("product_id"))
        price_bdt = row.get("price_bdt")
        try:
            price_bdt_float = float(price_bdt) if pd.notna(price_bdt) else 0.0
        except Exception:
            price_bdt_float = 0.0

        regular_price = row.get("regular_price_bdt (optional)")
        offer_price = row.get("offer_price_bdt (optional)")

        p_item = {
            "product_id": prid,
            "product_name": clean_val(row.get("product_name")),
            "category": clean_val(row.get("category")),
            "brand": clean_val(row.get("brand")),
            "size_or_dimension": clean_val(row.get("size_or_dimension")),
            "package_quantity": clean_val(row.get("package_quantity")),
            "price_bdt": price_bdt_float,
            "price_unit": clean_val(row.get("price_unit")),
            "seller_name": clean_val(row.get("seller_name")),
            "platform_name": clean_val(row.get("platform_name")),
            "product_url": clean_val(row.get("product_url")),
            "image_url": clean_val(row.get("image_url")),
            "availability": clean_val(row.get("availability")),
            "delivery_area": clean_val(row.get("delivery_area")),
            "collected_date": clean_val(row.get("collected_date")),
            "source_type": clean_val(row.get("source_type")),
            "verification_status": clean_val(row.get("verification_status")),
            "notes": clean_val(row.get("notes")),
            "regular_price_bdt": clean_val(regular_price),
            "offer_price_bdt": clean_val(offer_price),
            "source_log": prod_sources_map.get(prid),
        }
        products_json.append(p_item)

    out_products = research_dir / "verified_products.json"
    with open(out_products, "w", encoding="utf-8") as f:
        json.dump(products_json, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(products_json)} products to {out_products}")

    suppliers_json = []
    for _, row in df_suppliers.iterrows():
        sid = clean_val(row.get("supplier_id"))
        raw_contact = row.get("contact_number")
        contact_str = ""
        if pd.notna(raw_contact):
            digits = re.sub(r"\D", "", str(raw_contact))
            if digits.startswith("880"):
                contact_str = f"+{digits[:3]} {digits[3:7]}-{digits[7:]}"
            elif digits.startswith("01"):
                contact_str = f"+880 {digits[1:5]}-{digits[5:]}"
            elif digits.startswith("1"):
                contact_str = f"+880 {digits[:4]}-{digits[4:]}"
            else:
                contact_str = str(raw_contact)

        s_item = {
            "supplier_id": sid,
            "supplier_name": clean_val(row.get("supplier_name")),
            "supplier_type": clean_val(row.get("supplier_type")),
            "location": clean_val(row.get("location")),
            "contact_number": contact_str,
            "website_or_page": clean_val(row.get("website_or_page")),
            "product_categories": clean_val(row.get("product_categories")),
            "source_url": clean_val(row.get("source_url")),
            "seller_status": clean_val(row.get("seller_status")),
            "verification_date": clean_val(row.get("verification_date")),
            "notes": clean_val(row.get("notes")),
        }
        suppliers_json.append(s_item)

    out_suppliers = research_dir / "verified_suppliers.json"
    with open(out_suppliers, "w", encoding="utf-8") as f:
        json.dump(suppliers_json, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(suppliers_json)} suppliers to {out_suppliers}")

if __name__ == "__main__":
    convert_excel_to_json()
