import base64, hashlib, io, os, random, time, uuid
import requests
from .plant_matte import composite_plant_matte, parse_pins

PROMPT_VERSION = "v20"
VARIANTS = {"Productive", "Colorful", "Balanced"}

VARIANT_CLAUSE = {
    "Productive": "Emphasise heavy-fruiting edible crops such as tomatoes with ripe red fruit, chillies and brinjal in large grow bags and big pots.",
    "Colorful":   "Emphasise abundant flowers in bloom such as marigolds, roses and bougainvillea in glazed and terracotta pots.",
    "Balanced":   "Mix edible crops, culinary herbs and a few flowering plants in terracotta pots and black grow bags.",
}
LIGHTING_CLAUSE = {
    "daylight": "Keep the exact lighting and sun direction of the photo; make the plants brightly lit and vivid green, never dark or muddy.",
    "evening":  "Relight the whole scene as warm golden-hour evening light with long soft shadows; the plants stay clearly visible and not dark.",
    "shadow":   "Relight the whole scene as soft overcast daylight, even and bright, with no hard shadows.",
}
DEFAULT_PLANTS = {
    "Productive": "bushy green tomato plants with small red tomatoes, leafy green chili pepper plants, and bushy eggplant plants with broad leaves",
    "Colorful":   "blooming orange and yellow marigold bushes, flowering rose bushes, and lush bougainvillea",
    "Balanced":   "bushy green tomato plants with small red tomatoes, leafy green chili pepper plants, dense leafy green herb clusters, and blooming marigolds",
}

def _join(items):
    return items[0] if len(items) == 1 else (" and ".join(items) if len(items) == 2 else ", ".join(items[:-1]) + ", and " + items[-1])

PLANT_VISUAL_MAP = [
    (("tomato",), "bushy green tomato plants with small red tomatoes"),
    (("chilli", "chili", "pepper"), "leafy green chili pepper plants"),
    (("brinjal", "eggplant", "aubergine"), "bushy eggplant plants with broad leaves"),
    (("cucumber", "gourd"), "leafy green vegetable vines on bamboo trellises"),
    (("aloe",), "small potted aloe vera"),
    (("marigold",), "blooming orange and yellow marigold bushes"),
    (("rose",), "flowering rose bushes"),
    (("mint", "coriander", "basil", "herb"), "dense leafy green herb clusters"),
]

def _visual_plant_desc(name):
    if not name or not isinstance(name, str):
        return ""
    clean = name.strip()
    low = clean.lower()
    for keys, desc in PLANT_VISUAL_MAP:
        if any(k in low for k in keys):
            return desc
    return f"leafy green {clean} plant"

def build_flux_prompt(plants, variant, lighting, zones):
    variant = variant if variant in VARIANTS else "Balanced"
    lighting = lighting if lighting in LIGHTING_CLAUSE else "daylight"
    if plants:
        described = [_visual_plant_desc(p) for p in plants if p and isinstance(p, str)]
        seen = set()
        deduped = []
        for d in described:
            if d and d not in seen:
                seen.add(d)
                deduped.append(d)
        plant_txt = _join(deduped) if deduped else DEFAULT_PLANTS[variant]
    else:
        plant_txt = DEFAULT_PLANTS[variant]
    z = {(c.get("zone"), c.get("sun")) for c in (zones or []) if isinstance(c, dict)}
    kinds = {zz for zz, _ in z}
    parts = [
        "Add a rooftop container garden to the open concrete floor in this photo.",
        "Fill 75% to 85% of the visible concrete rooftop floor with tightly grouped clusters, continuous rows, and layered arrangements of 25 to 35 terracotta pots, wide raised wooden/brick planter beds, tiered plant racks, and large black grow bags packed with lush overflowing foliage, flowering marigolds, and leafy vegetables—leaving only a narrow walking path.",
        "Every pot has its base flat on the floor with a soft contact shadow beneath it.",
        f"Fill them with full, mature, healthy {plant_txt}, large and leafy, about waist to shoulder height.",
        "Every container must hold realistic, natural-scale leafy foliage, bushes, herbs, or flowers—never giant upright cacti or oversized standalone vegetables sticking straight out of soil.",
        VARIANT_CLAUSE[variant],
    ]
    if "WALKWAY" in kinds: parts.append("Leave the bare concrete walking aisle free of pots.")
    if "BLOCKED" in kinds: parts.append("Do not move, cover or alter the existing tanks, pipes and structures.")
    if ("GARDENING", "FULL_SUN") in z and ("GARDENING", "SHADE") in z:
        parts.append("Put sun-loving crops in the brightest open areas and leafy herbs in the shadier corners.")
    parts += [
        "Keep the parapet walls, the tops of the walls, railings, poles, wires, pipes, tanks, distant buildings and sky exactly as in the photo; the tops of the walls stay completely empty.",
        "Keep the same camera angle, perspective, framing and image size.",
        LIGHTING_CLAUSE[lighting],
    ]
    return " ".join(parts)

class RenderError(Exception):
    def __init__(self, code, message, http=502):
        super().__init__(message); self.code, self.message, self.http = code, message, http

def _seed(image_bytes, prompt, pins, nonce):
    basis = f"nonce:{nonce}" if nonce else hashlib.sha256(image_bytes).hexdigest() + prompt + repr(pins)
    return int(hashlib.sha256(basis.encode()).hexdigest()[:8], 16) % (2**31)

def render_garden(image_bytes, pins_norm, plants, variant, lighting, zones=None, nonce=None):
    token = os.getenv("REPLICATE_API_TOKEN", "").strip()
    if not token: raise RenderError("NO_REPLICATE_TOKEN", "REPLICATE_API_TOKEN is not configured on the server.", 503)
    import replicate
    t0 = time.time()
    pins = parse_pins(pins_norm)
    prompt = build_flux_prompt(plants, variant, lighting, zones)
    seed = _seed(image_bytes, prompt, pins, nonce)
    client = replicate.Client(api_token=token, timeout=120)
    ai_bytes, last_err = None, None
    for attempt in range(3):
        try:
            out = client.run("black-forest-labs/flux-kontext-pro", input={
                "prompt": prompt,
                "input_image": io.BytesIO(image_bytes),   # SAME bytes the frontend sent - no 1280px re-downscale
                "aspect_ratio": "match_input_image",
                "output_format": "png",                   # lossless; we do the only JPEG encode at the end
                "safety_tolerance": 2,                    # max allowed when an input image is used
                "prompt_upsampling": False,               # we already wrote a specific edit instruction
                "seed": seed,
            })
            url = str(out[0] if isinstance(out, (list, tuple)) else out)
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and len(r.content) > 5000:
                ai_bytes = r.content; break
            last_err = f"download status {r.status_code}"
            time.sleep(1)
        except Exception as e:
            last_err = str(e)
            err_lower = last_err.lower()
            if "429" in err_lower or "throttled" in err_lower:
                time.sleep(12)
            else:
                time.sleep(1)
        seed = (seed + 7919) % (2**31)                    # different seed on retry
    if not ai_bytes: raise RenderError("REPLICATE_FAILED", f"AI render failed: {last_err}")
    mode = "plant_matte" if lighting == "daylight" else "ai_full_frame"   # relit scenes change the whole frame
    debug = os.getenv("GARDEN_DEBUG_DIR") or None
    final, meta = composite_plant_matte(image_bytes, ai_bytes, pins, mode=os.getenv("GARDEN_COMPOSITE_MODE", mode), debug_dir=debug)
    return {
        "jpeg": final, "prompt": prompt, "seed": seed, "meta": meta, "prompt_version": PROMPT_VERSION,
        "request_id": uuid.uuid4().hex, "elapsed": round(time.time() - t0, 1),
    }
