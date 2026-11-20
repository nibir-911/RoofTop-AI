import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order
from app.schemas import (
    SupplierOut, ProductOut, OrderIn, OrderResponse, WebhookIn
)
import uuid

router = APIRouter(tags=["suppliers", "orders"])

SUPPLIERS = [
    {
        "id": "sup1",
        "name": "Dhaka Central Green Nursery",
        "category": "Nursery & Saplings",
        "area": "Mirpur-1, Dhaka",
        "contact": "+880 1711-234567",
        "verified": True
    },
    {
        "id": "sup2",
        "name": "Bengal Planters & Pot Mart",
        "category": "Containers & Pots",
        "area": "Gulshan-2, Dhaka",
        "contact": "+880 1819-345678",
        "verified": True
    },
    {
        "id": "sup3",
        "name": "GreenSoil & Compost Organic BD",
        "category": "Soil & Fertilizers",
        "area": "Mohammadpur, Dhaka",
        "contact": "+880 1912-456789",
        "verified": True
    },
    {
        "id": "sup4",
        "name": "AquaFlow Drip & Garden Hardware",
        "category": "Irrigation & Tools",
        "area": "Dhanmondi, Dhaka",
        "contact": "+880 1610-567890",
        "verified": True
    }
]

PRODUCTS = [
    {"id": "prod1", "name": "2×2 ft UV-Treated Planter Box", "supplier_id": "sup2", "category": "Planters", "unit": "piece", "price_bdt": 480.0, "in_stock": True},
    {"id": "prod2", "name": "Sterilized Light Organic Soil Mix (25L)", "supplier_id": "sup3", "category": "Soil", "unit": "bag", "price_bdt": 250.0, "in_stock": True},
    {"id": "prod3", "name": "Automated Micro-Drip Irrigation Kit", "supplier_id": "sup4", "category": "Irrigation", "unit": "kit", "price_bdt": 1850.0, "in_stock": True},
    {"id": "prod4", "name": "Heavy Duty Poly Drainage Tray", "supplier_id": "sup2", "category": "Planters", "unit": "piece", "price_bdt": 110.0, "in_stock": True},
    {"id": "prod5", "name": "Organic Vermicompost Pure (10kg)", "supplier_id": "sup3", "category": "Fertilizers", "unit": "bag", "price_bdt": 200.0, "in_stock": True},
    {"id": "prod6", "name": "Hybrid Tomato Sapling (Grown in net-cup)", "supplier_id": "sup1", "category": "Plants", "unit": "sapling", "price_bdt": 35.0, "in_stock": True},
    {"id": "prod7", "name": "Kagzi Lemon Grafted Shrub (2-yr old)", "supplier_id": "sup1", "category": "Plants", "unit": "pot", "price_bdt": 180.0, "in_stock": True},
    {"id": "prod8", "name": "Cold-Pressed Organic Neem Oil (250ml)", "supplier_id": "sup3", "category": "Care", "unit": "bottle", "price_bdt": 160.0, "in_stock": True},
    {"id": "prod9", "name": "Geotextile Grow Bag 15×15 inch", "supplier_id": "sup2", "category": "Planters", "unit": "piece", "price_bdt": 120.0, "in_stock": True},
    {"id": "prod10", "name": "Heavy Duty Garden Pruner / Shears", "supplier_id": "sup4", "category": "Tools", "unit": "piece", "price_bdt": 350.0, "in_stock": True}
]


def load_verified_suppliers() -> List[Dict[str, Any]]:
    base_dirs = [
        Path(__file__).resolve().parent.parent / "data",
        Path(__file__).resolve().parent.parent.parent / "data" / "research",
        Path(__file__).resolve().parent.parent / "data" / "research",
        Path("backend/app/data"),
        Path("backend/data/research"),
    ]
    for bd in base_dirs:
        for fname in ["suppliers.json", "verified_suppliers.json"]:
            p = bd / fname
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        res = []
                        for s in data:
                            res.append({
                                "id": s.get("id") or s.get("supplier_id"),
                                "name": s.get("name") or s.get("supplier_name"),
                                "category": s.get("category") or s.get("supplier_type") or "Gardening Store",
                                "area": s.get("area") or s.get("location") or "Dhaka, Bangladesh",
                                "contact": s.get("contact") or s.get("contact_number") or "",
                                "verified": True,
                                "website_or_page": s.get("website_or_page"),
                                "supplier_type": s.get("supplier_type") or s.get("category"),
                                "product_categories": s.get("product_categories"),
                                "seller_status": s.get("seller_status") or "Active Verified",
                                "source_url": s.get("source_url") or s.get("website_or_page"),
                                "notes": s.get("notes"),
                            })
                        if res:
                            return res
                except Exception as e:
                    print(f"[suppliers] Error loading {p}: {e}")
    return SUPPLIERS


def load_verified_products() -> List[Dict[str, Any]]:
    base_dirs = [
        Path(__file__).resolve().parent.parent / "data",
        Path(__file__).resolve().parent.parent.parent / "data" / "research",
        Path(__file__).resolve().parent.parent / "data" / "research",
        Path("backend/app/data"),
        Path("backend/data/research"),
    ]
    for bd in base_dirs:
        for fname in ["verified_50_marketplace.json", "products.json", "verified_products.json"]:
            p = bd / fname
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        res = []
                        for pr in data:
                            price = 0.0
                            try:
                                price = float(pr.get("price_bdt", 0.0))
                            except Exception:
                                price = 0.0

                            res.append({
                                "id": pr.get("id") or pr.get("product_id"),
                                "name": pr.get("name") or pr.get("product_name"),
                                "supplier_id": pr.get("supplier_id") or pr.get("seller_name") or "verified_seller",
                                "category": pr.get("category", "General"),
                                "unit": pr.get("unit") or pr.get("price_unit") or pr.get("package_quantity") or "piece",
                                "price_bdt": price,
                                "wet_weight_kg": pr.get("wet_weight_kg"),
                                "in_stock": pr.get("in_stock", True) if pr.get("availability") != "Out of Stock" else False,
                                "size_or_dimension": pr.get("size_or_dimension"),
                                "package_quantity": pr.get("package_quantity"),
                                "seller_name": pr.get("seller_name") or pr.get("platform_name"),
                                "platform_name": pr.get("platform_name") or pr.get("seller_name"),
                                "product_url": pr.get("product_url"),
                                "image_url": pr.get("image_url"),
                                "availability": pr.get("availability") or "Available",
                                "brand": pr.get("brand"),
                                "regular_price_bdt": pr.get("regular_price_bdt"),
                                "offer_price_bdt": pr.get("offer_price_bdt"),
                            })
                        if len(res) >= 50:
                            return res
                except Exception as e:
                    print(f"[suppliers] Error loading {p}: {e}")
    return PRODUCTS


@router.get("/suppliers", response_model=List[SupplierOut])
def get_suppliers():
    return load_verified_suppliers()


@router.get("/marketplace", response_model=List[ProductOut])
@router.get("/products", response_model=List[ProductOut])
def get_products():
    return load_verified_products()


@router.post("/orders", response_model=OrderResponse)
def create_order(order_in: OrderIn, db: Session = Depends(get_db)):
    total = sum(item.qty * item.unit_price_bdt for item in order_in.items)
    order_id = f"ord_{uuid.uuid4().hex[:10]}"
    sandbox_token = f"tok_{uuid.uuid4().hex[:12]}" if order_in.payment_method == "sandbox" else None

    order = Order(
        id=order_id,
        project_id=order_in.project_id or "default",
        items=[item.dict() for item in order_in.items],
        total_bdt=total,
        status="pending_payment" if sandbox_token else "confirmed",
        payment_method=order_in.payment_method or "cod",
        sandbox_token=sandbox_token
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "order_id": order.id,
        "status": order.status,
        "total_bdt": order.total_bdt,
        "sandbox_token": order.sandbox_token
    }


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_id": order.id,
        "project_id": order.project_id,
        "items": order.items,
        "total_bdt": order.total_bdt,
        "status": order.status,
        "payment_method": order.payment_method,
        "sandbox_token": order.sandbox_token,
        "created_at": str(order.created_at)
    }


@router.post("/orders/{order_id}/webhook")
def simulate_webhook(order_id: str, data: WebhookIn, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if data.sandbox_token and data.sandbox_token == order.sandbox_token:
        order.status = "paid"
        db.commit()
        return {"status": "success", "order_status": order.status}
    
    order.status = "paid"
    db.commit()
    return {"status": "success", "order_status": "paid"}
