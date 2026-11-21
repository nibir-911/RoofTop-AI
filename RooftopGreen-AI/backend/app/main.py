from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.routes import preferences, roof, garden, plants_routes, suppliers, plant_doctor, visualizer, generate_design, roof_detect
import os

cors_origins_env = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,https://rooftop-ai.vercel.app",
)
allowed_origins = [
    origin.strip().rstrip("/")
    for origin in cors_origins_env.split(",")
    if origin.strip()
]

app = FastAPI(title="RooftopGreen AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

app.include_router(preferences.router, prefix="/api")
app.include_router(roof.router, prefix="/api")
app.include_router(garden.router, prefix="/api")
app.include_router(plants_routes.router, prefix="/api")
app.include_router(suppliers.router, prefix="/api")
app.include_router(plant_doctor.router, prefix="/api")
app.include_router(visualizer.router, prefix="/api")
app.include_router(generate_design.router, prefix="/api")
app.include_router(roof_detect.router, prefix="/api")

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "RooftopGreen AI"}
