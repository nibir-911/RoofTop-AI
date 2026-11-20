import os
import io
import json
import re
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv

load_dotenv("backend/.env")
from google import genai

key = os.getenv("GEMINI_API_KEY")
print("Key exists:", bool(key))
client = genai.Client(api_key=key)

img_paths = [
    Path("public/images/view1.jpg"),
    Path("RoofTop-AI-main/public/images/view1.jpg"),
    Path("RoofTop-AI-main/RoofTop-AI-main/public/images/view1.jpg"),
]
img_path = next((p for p in img_paths if p.exists()), None)
print("Image path:", img_path)
pil_img = Image.open(img_path).convert("RGB")
pil_img.thumbnail((800, 600))

prompt = (
    "Analyze this rooftop photograph to detect the walkable floor surface.\n"
    "Return ONLY a valid JSON object with:\n"
    '1. "perimeter_points": list of 4 to 6 normalized coordinates [{"x": float, "y": float}, ...] between 0.0 and 1.0 outlining ONLY the flat walkable concrete floor surface.\n'
    "- Strictly exclude sky, parapet walls, railings, ledges, and neighboring buildings.\n"
    "- The top edge of the polygon should trace where the back/side walls meet the floor surface.\n"
    '2. "obstacles": list of objects on the floor [{"label": str, "x": float, "y": float, "width": float, "height": float}], or [] if none.\n'
    '3. "floor_confidence": float between 0.0 and 1.0.\n'
    "Return raw JSON only, no markdown."
)

models = ["gemini-3.5-flash", "gemini-3.8-flash"]
for m in models:
    try:
        resp = client.models.generate_content(model=m, contents=[pil_img, prompt])
        print(f"Model {m} output:\n{resp.text}")
        cleaned = re.sub(r"^```(?:json)?\s*", "", resp.text.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        data = json.loads(cleaned)
        print("Parsed JSON successfully:", data)
        break
    except Exception as e:
        print(f"Model {m} error: {e}")
