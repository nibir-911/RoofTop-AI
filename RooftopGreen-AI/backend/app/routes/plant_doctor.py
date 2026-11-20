import os
import re
import json
import base64
import io
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from PIL import Image
from app.schemas import PlantDoctorIn, PlantDoctorResponse, PlantDoctorChatIn

# Google GenAI SDK import
try:
    from google import genai
except ImportError:
    genai = None

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

router = APIRouter(prefix="/plant-doctor", tags=["plant-doctor"])

# ---------------------------------------------------------------------------
# Load Gemini API Key
# ---------------------------------------------------------------------------

def get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        return key
    env_paths = [
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
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

GEMINI_API_KEY = get_gemini_api_key()
genai_client = None
if genai and GEMINI_API_KEY:
    try:
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"[plant_doctor] Gemini Client init note: {e}")

# ---------------------------------------------------------------------------
# Curated Rooftop Agronomy Knowledge Base (RAG)
# ---------------------------------------------------------------------------

_KB_CACHE: List[Dict[str, Any]] = []

def load_kb_data() -> List[Dict[str, Any]]:
    global _KB_CACHE
    if _KB_CACHE:
        return _KB_CACHE

    candidates = [
        Path(__file__).resolve().parent.parent / "data" / "plant_rag_kb.json",
        Path(__file__).resolve().parent.parent.parent / "data" / "plant_rag_kb.json",
        Path("backend/app/data/plant_rag_kb.json"),
        Path("backend/data/plant_rag_kb.json"),
    ]
    for c in candidates:
        if c.exists():
            try:
                with open(c, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        _KB_CACHE = data
                        print(f"[plant_doctor] Loaded {len(_KB_CACHE)} RAG knowledge documents from {c}")
                        return _KB_CACHE
            except Exception as e:
                print(f"[plant_doctor] Error loading {c}: {e}")
    return []

# Eagerly pre-cache RAG knowledge base at startup so it is loaded once in memory
_KB_CACHE = load_kb_data()

# ---------------------------------------------------------------------------
# RAG Document Retriever
# ---------------------------------------------------------------------------

STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is",
    "are", "was", "were", "my", "your", "our", "i", "how", "what", "why", "can",
    "do", "does", "with", "from", "by", "about", "me", "this", "that", "it"
}

CROP_ALIASES = {
    "tomato": ["tomato", "tomatoes", "solanum"],
    "chilli": ["chilli", "chillies", "chili", "pepper", "peppers", "capsicum", "morich"],
    "brinjal": ["brinjal", "eggplant", "aubergine", "begun"],
    "lemon": ["lemon", "lemons", "lime", "citrus", "lebu", "malta", "kagzi"],
    "gourd": ["gourd", "gourds", "lau", "kaddu", "cucumber", "squash", "cucurbit"],
    "mint": ["mint", "pudina"],
    "marigold": ["marigold", "genda"],
    "guava": ["guava", "peara"],
}

def tokenize(text: str) -> List[str]:
    clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
    return [w for w in clean.split() if len(w) > 2 and w not in STOP_WORDS]

def retrieve_relevant_docs(
    query: str,
    diagnosis_context: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, Any]]] = None,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    docs = load_kb_data()
    if not docs:
        return []

    q_tokens = set(tokenize(query))

    # Add diagnosis context tokens if present
    diag_tokens = set()
    if diagnosis_context:
        diag_parts = [
            str(diagnosis_context.get("disease") or ""),
            str(diagnosis_context.get("primary_cause") or ""),
            " ".join(diagnosis_context.get("symptoms") or []) if isinstance(diagnosis_context.get("symptoms"), list) else str(diagnosis_context.get("symptoms") or ""),
            str(diagnosis_context.get("crop") or ""),
            " ".join(diagnosis_context.get("alternative_causes") or []) if isinstance(diagnosis_context.get("alternative_causes"), list) else ""
        ]
        diag_tokens = set(tokenize(" ".join(diag_parts)))

    # Extract tokens from recent history (last 4-6 messages)
    history_user_tokens = set()
    history_asst_tokens = set()
    if history:
        for turn in history[-6:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            tokens = set(tokenize(content))
            if role == "user":
                history_user_tokens.update(tokens)
            else:
                history_asst_tokens.update(tokens)

    # Detect follow-up or referential query patterns
    full_q = query.lower().strip()
    is_referential = (
        len(q_tokens) <= 3 or
        any(k in full_q for k in [
            "why", "cause", "causes", "reason", "happen", "happens", "occur", "how come",
            "this", "it", "that", "these", "how much", "ratio", "recipe", "mixing",
            "cure", "treat", "prevent", "spray", "what about", "tell me more"
        ])
    )

    scored_docs = []
    for doc in docs:
        score = 0.0
        doc_title = str(doc.get("title", "")).lower()
        doc_crop = str(doc.get("crop", "")).lower()
        doc_symptoms = str(doc.get("symptoms", "")).lower()
        doc_treatment = str(doc.get("treatment", "")).lower()
        doc_prevention = str(doc.get("prevention", "")).lower()

        title_tokens = set(tokenize(doc_title))
        crop_tokens = set(tokenize(doc_crop))
        symptom_tokens = set(tokenize(doc_symptoms))
        treatment_tokens = set(tokenize(doc_treatment))

        # 1. Query overlap
        score += len(q_tokens & title_tokens) * 8.0
        score += len(q_tokens & crop_tokens) * 8.0
        score += len(q_tokens & symptom_tokens) * 4.0
        score += len(q_tokens & treatment_tokens) * 3.0

        # 2. Crop alias match boost
        all_candidate_tokens = q_tokens | diag_tokens | (history_user_tokens if is_referential else set())
        for crop_group, aliases in CROP_ALIASES.items():
            if any(a in all_candidate_tokens for a in aliases):
                if any(a in doc_crop or a in doc_title for a in aliases):
                    score += 10.0

        # 3. Diagnosis context overlap (high priority from leaf diagnosis)
        if diag_tokens:
            score += len(diag_tokens & title_tokens) * 7.0
            score += len(diag_tokens & crop_tokens) * 6.0
            score += len(diag_tokens & symptom_tokens) * 4.0
            score += len(diag_tokens & treatment_tokens) * 3.0

        # 4. History overlap (crucial for follow-up questions like 'why this happens?')
        hist_weight = 3.5 if is_referential else 1.5
        score += len(history_user_tokens & title_tokens) * (hist_weight * 1.5)
        score += len(history_user_tokens & crop_tokens) * (hist_weight * 1.5)
        score += len(history_user_tokens & symptom_tokens) * hist_weight
        score += len(history_asst_tokens & title_tokens) * (hist_weight * 1.0)
        score += len(history_asst_tokens & crop_tokens) * (hist_weight * 1.0)

        # 5. Targeted phrase boosts
        target_texts = [full_q]
        if is_referential and history:
            target_texts.append(" ".join(t.get("content", "") for t in history[-2:]).lower())
        combined_text = " ".join(target_texts)

        if "neem" in full_q and ("neem" in doc_treatment or "neem" in doc_title):
            score += 12.0
        if "mealybug" in combined_text and "mealybug" in doc_title:
            score += 15.0
        if "curl" in combined_text and "curl" in doc_title:
            score += 15.0
        if "mildew" in combined_text and "mildew" in doc_title:
            score += 15.0
        if "blossom" in combined_text and "blossom" in doc_title:
            score += 15.0
        if "spider" in combined_text and "mite" in combined_text and "mite" in doc_title:
            score += 15.0
        if "yellow" in combined_text and ("yellow" in doc_symptoms or "chlorosis" in doc_title or "nitrogen" in doc_title):
            score += 8.0
        if "fertiliz" in combined_text and ("vermicompost" in doc_treatment or "nitrogen" in doc_title):
            score += 6.0
        if "rot" in combined_text and "root" in combined_text and "root_rot" in doc.get("id", ""):
            score += 15.0

        scored_docs.append((score, doc))

    # Sort descending by score
    scored_docs.sort(key=lambda x: x[0], reverse=True)

    # Return only docs with positive match score
    positive_docs = [doc for score, doc in scored_docs if score > 0.0]
    if positive_docs:
        return positive_docs[:top_k]

    # Contextual fallback when score is 0: Check diagnosis or history for matches
    if diagnosis_context:
        diag_str = str(diagnosis_context.get("primary_cause") or diagnosis_context.get("disease") or "").lower()
        if diag_str:
            for doc in docs:
                if any(w in doc.get("title", "").lower() for w in diag_str.split() if len(w) > 3):
                    return [doc]

    if history:
        hist_str = " ".join(t.get("content", "") for t in history[-4:]).lower()
        for doc in docs:
            if doc.get("id") in hist_str or doc.get("crop", "").lower().split()[0] in hist_str:
                return [doc]

    # Never blindly return index 0; return empty so synthesizer handles it cleanly
    return []


# ---------------------------------------------------------------------------
# Smart Fallback Synthesizer (Varies responses by intent & context)
# ---------------------------------------------------------------------------

def synthesize_fallback_response(
    query: str,
    top_doc: Optional[Dict[str, Any]],
    history: List[Dict[str, Any]],
    diagnosis_context: Optional[Dict[str, Any]]
) -> str:
    lower_q = (query or "").lower().strip()

    # Intent Detection
    is_why = any(w in lower_q for w in ["why", "cause", "causes", "reason", "happen", "happens", "occur", "vector", "how come", "origin"])
    is_dosage = any(w in lower_q for w in ["how much", "ratio", "recipe", "mixing", "dose", "dosage", "formula", "proportion", "dilut", "measurement", "ml", "quantity"])
    is_treatment = any(w in lower_q for w in ["cure", "treat", "treatment", "remedy", "fix", "solve", "how to treat", "medicine", "spray", "action"])
    is_prevention = any(w in lower_q for w in ["prevent", "prevention", "avoid", "stop", "next time", "future", "protect", "safe"])

    # If no specific doc matched, provide intelligent urban agronomy guidance (NEVER static index 0)
    if not top_doc:
        if is_why:
            return (
                "### Why Rooftop Plant Problems Occur in Dhaka\n\n"
                "**Authority:** BARI Rooftop Gardening & Climate Adaptation Manual\n\n"
                "• **Extreme Thermal Radiation:** Concrete roofs absorb solar heat all day, reaching floor temperatures of 40°C–45°C. This radiates upward, rapidly drying shallow container soil and stressing delicate root tips.\n"
                "• **Urban Pest Updrafts:** Thermal updrafts in densely built Dhaka neighborhoods carry microscopic pests (silverleaf whiteflies, aphids, thrips, and fungal spores) from street-level foliage directly up to rooftop gardens.\n"
                "• **Container Soil Leaching:** Daily watering in small potting containers quickly washes away mobile nitrogen and trace minerals, causing sudden yellowing and leaf chlorosis.\n"
                "• **Recommendation:** Place containers on 2-inch wooden or clay risers to block concrete heat conduction, mulch with coconut coir, and spray organic neem emulsion every 10 days."
            )
        elif is_dosage or "neem" in lower_q:
            return (
                "### BARI Standard Organic Neem Oil Mixing Ratios & Preparation\n\n"
                "**Authority:** BARI Bio-Pesticide Standard Operating Protocol\n"
                "**Target:** Safe control of sap-sucking insects (aphids, mites, whiteflies, mealybugs)\n\n"
                "**Standard Formula (Per 1 Litre of Water):**\n"
                "• **Cold-Pressed Neem Oil:** 5 ml (min 1500 ppm Azadirachtin)\n"
                "• **Liquid Soap / Baby Shampoo:** 2 ml (as emulsifier)\n"
                "• **Lukewarm Water:** 1 Litre (~30°C helps dissolve oil)\n\n"
                "**Preparation Method:**\n"
                "1. Mix 2 ml soap in 100 ml lukewarm water until foamy.\n"
                "2. Add 5 ml neem oil and shake vigorously in a bottle for 60 seconds until a milky white emulsion forms.\n"
                "3. Top up with remaining 900 ml water. Spray within 4 hours.\n\n"
                "**Application Rule:** Spray late afternoon (after 4:30 PM) on leaf undersides. Repeat every 4–5 days for active pests, or every 10–14 days as a preventive barrier."
            )
        else:
            return (
                "### General Rooftop Plant Health Guidelines (BARI & DAE Standards)\n\n"
                "• **Watering Timing:** Water deeply before 8:00 AM so container roots are fully hydrated before concrete floor heating begins.\n"
                "• **Soil Aeration & Mulch:** Top-dress containers with 2 handfuls of rich vermicompost and a 2-inch layer of dry leaf mulch to retain moisture.\n"
                "• **Preventive Foliar Spray:** Apply cold-pressed neem oil emulsion (5ml neem + 2ml liquid soap per 1L water) every 10–14 days in the late afternoon to deter sap-sucking vectors.\n"
                "• **Container Drainage:** Ensure all planter drainage holes are unblocked and pots are elevated on pot-feet to prevent stagnant root rot."
            )

    title = top_doc.get("title", "Plant Health Condition")
    crop = top_doc.get("crop", "Container Vegetables & Fruits")
    source = top_doc.get("source", "BARI Rooftop Agriculture Manual")
    symptoms = top_doc.get("symptoms", "")
    treatment = top_doc.get("treatment", "")
    prevention = top_doc.get("prevention", "")
    doc_id = top_doc.get("id", "")

    # Check if immediate previous assistant turn already covered this exact doc title
    already_discussed = False
    if history:
        for t in reversed(history[-3:]):
            if t.get("role") == "assistant" and title.lower() in t.get("content", "").lower():
                already_discussed = True
                break

    # CASE A: Follow-up on "Why this happens"
    if is_why:
        cause_details = ""
        if "curl" in doc_id or "virus" in doc_id or "whitefly" in doc_id:
            cause_details = (
                "• **Biological Vector:** Transmitted by silverleaf whiteflies (*Bemisia tabaci*) that feed on leaf sap. Once inside the phloem, the geminivirus disrupts growth hormones (auxin and gibberellin synthesis).\n"
                "• **Why Leaves Cup & Curl:** Viral replication causes uneven cell division in the leaf lamina, resulting in upward curling, thickened brittle texture, and abrupt flower drop.\n"
                "• **Dhaka Rooftop Factors:** Concrete slab temperatures (38°C+) accelerate whitefly reproduction cycles from 30 days down to 14 days, while urban thermal updrafts carry insects up from ground level."
            )
        elif "mealybug" in doc_id:
            cause_details = (
                "• **Biological Mechanism:** Cottony mealybugs (*Planococcus citri*) colonize leaf nodes and fruit clusters, using piercing mouthparts to drink carbohydrate-rich sap.\n"
                "• **Why Black Mold Forms:** Mealybugs excrete excess sugar as sticky 'honeydew', which serves as the substrate for secondary black sooty mold (*Capnodium spp.*), blocking photosynthesis.\n"
                "• **Rooftop Factors:** Warm, unventilated corners between clustered containers and concrete parapet walls create the ideal shelter for mealybug egg sacs."
            )
        elif "mildew" in doc_id:
            cause_details = (
                "• **Fungal Pathogen:** Caused by airborne conidia spores (*Podosphaera xanthii*). Unlike most fungi, powdery mildew does not need free water on leaves to germinate.\n"
                "• **Why White Dust Appears:** Fungal hyphae tap directly into epidermal cells, rapidly spreading millions of powdery white surface spores across upper foliage.\n"
                "• **Rooftop Factors:** High relative humidity (65%–85%) combined with dense foliage and stagnant air between closely packed rooftop containers triggers spore bursts."
            )
        elif "blossom" in doc_id:
            cause_details = (
                "• **Physiological Calcium Deficit:** Blossom End Rot is not an infection, but a localized calcium (Ca) transport failure in rapidly expanding fruit tissue.\n"
                "• **Why Black Sunken Spots Form:** Calcium is an immobile element carried solely through the water transpiration stream. Rapid evaporation on sunny roofs causes moisture stress, halting calcium delivery to fruit blossom ends where cell walls collapse.\n"
                "• **Rooftop Factors:** Small container potting volume dries out quickly under midday sun, creating dramatic wet-dry cycles that stall calcium absorption."
            )
        elif "nitrogen" in doc_id or "chlorosis" in doc_id:
            cause_details = (
                "• **Mobile Nutrient Translocation:** Nitrogen is a mobile element in plant tissue. When root supply is exhausted, the plant mobilizes nitrogen from older lower leaves to support new apical growth.\n"
                "• **Why Lower Leaves Turn Yellow First:** Chlorophyll in older leaves breaks down to feed growing tips, leaving lower leaves uniformly pale yellow (chlorotic).\n"
                "• **Rooftop Factors:** Daily summer irrigation in containers leaches soluble nitrates out of drainage holes faster than soil microorganisms can replenish them."
            )
        elif "root_rot" in doc_id:
            cause_details = (
                "• **Root Hypoxia & Fungal Attack:** When container soil remains waterlogged, oxygen is depleted from root pores (anaerobic state), suffocating root hairs.\n"
                "• **Why Plants Wilt in Wet Soil:** Water mold pathogens (*Pythium* / *Phytophthora*) invade decayed roots, destroying water-absorbing xylem vessels so the plant paradoxically wilts despite moist soil.\n"
                "• **Rooftop Factors:** Heavy clay garden soil in pots without adequate coarse drainage sand or blocked bottom holes during monsoon rain."
            )
        elif "spider_mite" in doc_id:
            cause_details = (
                "• **Explosive Dry-Heat Life Cycle:** Two-spotted spider mites (*Tetranychus urticae*) multiply exponentially at temperatures above 32°C, completing generations in 5–7 days.\n"
                "• **Why Foliage Stipples & Dries:** Millions of microscopic mites puncture cells under leaf surfaces to suck chlorophyll, producing fine yellow stippling and silk webbing.\n"
                "• **Rooftop Factors:** Hot, dusty air and concrete thermal radiation create dry microclimates that eliminate natural predatory insects."
            )
        else:
            cause_details = (
                "• **Primary Environmental & Biological Drivers:** Urban rooftop plants endure high solar radiation, wind drafts, and limited container soil volumes.\n"
                f"• **Condition Characteristics:** {symptoms}\n"
                "• **Rooftop Stress Multipliers:** Concrete floor heat radiation (40°C+) creates intense evaporative pull and triggers pest vectors."
            )

        prefix = "💡 *Follow-up Agronomic Context:* Continuing our discussion on **" + title + "**:\n\n" if already_discussed else ""
        return (
            f"{prefix}### Root Causes & Why This Happens: {title}\n\n"
            f"**Target Crop:** {crop}\n"
            f"**Authority Source:** {source}\n\n"
            f"**1. Causal Biology & Mechanisms:**\n{cause_details}\n\n"
            f"**2. Noticeable Symptoms:**\n{symptoms}\n\n"
            f"**3. Immediate Agronomic Action Steps:**\n"
            f"• Follow standard BARI organic treatment: spray cold-pressed neem oil (5ml neem + 2ml soap per 1L water) late afternoon to break pest cycles.\n"
            f"• Ensure containers are spaced 45 cm apart on pot-feet for cross-ventilation."
        )

    # CASE B: Follow-up on "How much neem oil / mixing ratios / dosage"
    if is_dosage or "neem" in lower_q:
        return (
            f"### BARI Standard Organic Mixing Ratios: {title}\n\n"
            f"**Authority Protocol:** BARI Bio-Pesticide Standard Operating Protocol\n"
            f"**Target Application:** Safe control of pests for {crop}\n\n"
            f"**Exact Formula (Per 1 Litre of Water):**\n"
            f"• **Pure Cold-Pressed Neem Oil:** 5 ml (minimum 1500 ppm Azadirachtin)\n"
            f"• **Mild Liquid Soap or Baby Shampoo:** 2 ml (acts as emulsifier so oil blends with water)\n"
            f"• **Lukewarm Water:** 1 Litre (~30°C helps dissolve oil)\n\n"
            f"**Preparation Instructions:**\n"
            f"1. Dissolve 2 ml of liquid soap in 100 ml of lukewarm water until foamy.\n"
            f"2. Add 5 ml neem oil into the soapy water and shake vigorously in a bottle for 60 seconds until a uniform milky white emulsion forms with zero free-floating oil drops.\n"
            f"3. Top up with remaining 900 ml water and spray immediately (within 4 hours of mixing).\n\n"
            f"**Rooftop Application Rules:**\n"
            f"• **Timing:** Spray strictly in the late afternoon (after 4:30 PM). Midday spraying under intense sun will cause foliar solar scorch.\n"
            f"• **Coverage:** Thoroughly spray the undersides of leaves and growing tips where pests hide.\n"
            f"• **Frequency:** Repeat every 4–5 days for active infestations (3 applications total); spray every 10–14 days for preventive maintenance."
        )

    # CASE C: Follow-up on "How to treat / cure / fix"
    if is_treatment:
        return (
            f"### Organic Treatment Protocol: {title}\n\n"
            f"**Target Crop:** {crop}\n"
            f"**Authority Source:** {source}\n\n"
            f"**Curative Steps:**\n{treatment}\n\n"
            f"**Practical Rooftop Tips:**\n"
            f"• Spray during calm late afternoons (after 4:30 PM) so wind does not blow droplets away.\n"
            f"• Rogue (remove) heavily diseased leaves and discard away from the rooftop garden.\n"
            f"• Drench container soil with diluted vermiwash (1:4 with water) to boost root resilience."
        )

    # CASE D: Follow-up on "How to prevent / avoid"
    if is_prevention:
        return (
            f"### Preventive Strategy & Container Management: {title}\n\n"
            f"**Target Crop:** {crop}\n"
            f"**Authority Source:** {source}\n\n"
            f"**Long-Term Prevention Plan:**\n{prevention}\n\n"
            f"**Urban Rooftop Best Practices:**\n"
            f"• **Container Spacing:** Maintain 40–50 cm between pots to allow Dhaka breeze to circulate freely.\n"
            f"• **Pot Elevation:** Elevate containers on clay pot-feet to prevent direct heat transfer from concrete roofs.\n"
            f"• **Hygiene:** Sterilize pruning shears with rubbing alcohol between plants to prevent viral spread."
        )

    # CASE E: Default / Initial Inquiry
    return (
        f"### {title}\n\n"
        f"**Authority Source:** {source}\n"
        f"**Target Crop:** {crop}\n\n"
        f"**Symptoms & Diagnosis:**\n{symptoms}\n\n"
        f"**Organic Treatment Protocol:**\n{treatment}\n\n"
        f"**Rooftop Prevention Strategy:**\n{prevention}\n\n"
        f"_Grounded in verified BARI/DAE urban agronomy standards._"
    )

# ---------------------------------------------------------------------------
# Traditional Heuristic Analysis Endpoint (Preserved)
# ---------------------------------------------------------------------------

RULES = [
    {
        "keywords": ["yellow", "yellowing", "pale"],
        "primary": "Nitrogen deficiency or over-watering",
        "confidence": 88,
        "label": "High Confidence",
        "alternatives": ["Iron chlorosis", "Insufficient drainage in root container"],
        "questions": ["Are older lower leaves yellowing first?", "Does the pot stay wet for more than 48 hours?"],
        "steps": [
            "Inspect container bottom drainage holes to ensure no stagnant water.",
            "Apply 1-2 handfuls of rich vermicompost or diluted mustard cake liquid fertilizer.",
            "Allow top 2 inches of soil to dry out before next irrigation."
        ]
    },
    {
        "keywords": ["white", "powder", "mildew", "spots"],
        "primary": "Powdery Mildew (Fungal Infection)",
        "confidence": 84,
        "label": "High Confidence",
        "alternatives": ["Spider mite webbing", "Hard water mineral deposits"],
        "questions": ["Is white dust easily wiped off by finger?", "Are plants crowded without good air circulation?"],
        "steps": [
            "Prune severely affected leaves and dispose away from the rooftop garden.",
            "Spray with baking soda solution (1 tsp baking soda + 1/2 tsp dish soap per litre water).",
            "Space containers out to allow Dhaka breeze to circulate freely."
        ]
    },
    {
        "keywords": ["curl", "curling", "aphid", "sticky", "ant"],
        "primary": "Aphid or Whitefly Infestation",
        "confidence": 90,
        "label": "High Confidence",
        "alternatives": ["Heat stress leaf curl", "Thrips or mite damage"],
        "questions": ["Do you notice tiny green/black insects on the undersides of new leaves?", "Is there sticky honeydew substance?"],
        "steps": [
            "Wash affected stems with a strong water spray jet in early morning.",
            "Spray neem oil organic solution (5ml neem oil + 2ml liquid soap per 1L lukewarm water) every 5-7 days.",
            "Introduce or protect beneficial ladybug beetles."
        ]
    },
    {
        "keywords": ["brown", "dry", "crispy", "edges", "tip"],
        "primary": "Moisture Stress or Potassium Deficiency",
        "confidence": 80,
        "label": "Medium Confidence",
        "alternatives": ["Excessive solar scorch during midday", "Fertilizer salt burn"],
        "questions": ["Are containers exposed to direct western afternoon heat?", "Has liquid fertilizer been applied recently?"],
        "steps": [
            "Provide light afternoon shade net (30-50% green mesh) during hot months.",
            "Water deeply early morning before 8:00 AM.",
            "Mulch the planter topsoil with 2 inches of dried leaves or coco chips."
        ]
    }
]

@router.post("/analyze", response_model=PlantDoctorResponse)
def analyze_plant_disease(data: PlantDoctorIn):
    # -----------------------------------------------------------------------
    # 1. Gemini Vision AI Analysis (when image_base64 is provided)
    # -----------------------------------------------------------------------
    if data.image_base64 and genai_client:
        try:
            raw_b64 = data.image_base64
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(raw_b64)
            pil_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            # 1. Image Compression: resize to max 768x768 and compress as JPEG (quality=75) in memory
            pil_image.thumbnail((768, 768), Image.Resampling.LANCZOS)
            jpeg_buf = io.BytesIO()
            pil_image.save(jpeg_buf, format="JPEG", quality=75, optimize=True)
            jpeg_buf.seek(0)
            pil_image = Image.open(jpeg_buf)

            # 2. RAG Caching & Top-K: retrieve top 3 most relevant chunks (cached in memory)
            symptoms_str = ", ".join(data.symptoms) if data.symptoms else "Visual inspection of leaf abnormalities"
            top_docs = retrieve_relevant_docs(symptoms_str, top_k=3)
            rag_lines = []
            for doc in top_docs:
                title = doc.get("title") or doc.get("disease") or "BARI Agronomy Reference"
                crops = ", ".join(doc.get("crops", []))
                symptoms_summary = doc.get("symptoms", "")[:100]
                rag_lines.append(f"- {title} (crops: {crops}): {symptoms_summary}")
            rag_context_str = "\n".join(rag_lines) if rag_lines else "BARI rooftop disease reference"

            # 3. Fast Concise Output: concise prompt requesting 3 short treatment steps
            vision_prompt = (
                "You are an expert Urban Plant Pathologist specializing in rooftop agriculture in Dhaka, Bangladesh (BARI and DAE standards).\n"
                "Visually examine this leaf photo for disease, pest damage, or nutrient deficiencies.\n"
                f"User symptoms: {symptoms_str}.\n"
                f"Top 3 BARI/DAE reference conditions:\n{rag_context_str}\n\n"
                "Respond strictly as a concise JSON object with no markdown backticks:\n"
                "{\n"
                '  "diagnosis": "Clear disease or deficiency name",\n'
                '  "confidence": 90,\n'
                '  "confidence_label": "High Confidence",\n'
                '  "severity": "Moderate",\n'
                '  "alternative_causes": ["Cause 1", "Cause 2"],\n'
                '  "care_steps": [\n'
                '    "Step 1: Immediate organic action...",\n'
                '    "Step 2: Mixing ratio...",\n'
                '    "Step 3: Cultural or watering adjustment..."\n'
                '  ],\n'
                '  "organic_remedy": "Short organic spray formulation",\n'
                '  "prevention": "Short container prevention advice"\n'
                "}"
            )

            # Fast Flash candidate models prioritized for speed and current quota availability
            candidate_models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash"]
            fast_config = None
            if hasattr(genai, "types") and hasattr(genai.types, "GenerateContentConfig"):
                fast_config = genai.types.GenerateContentConfig(max_output_tokens=450)

            for model_name in candidate_models:
                try:
                    kwargs = {"model": model_name, "contents": [pil_image, vision_prompt]}
                    if fast_config:
                        kwargs["config"] = fast_config

                    response = genai_client.models.generate_content(**kwargs)
                    if response and response.text:
                        raw_text = response.text.strip()
                        if raw_text.startswith("```"):
                            raw_text = re.sub(r"^```(?:json)?", "", raw_text, flags=re.IGNORECASE).strip()
                            raw_text = re.sub(r"```$", "", raw_text).strip()

                        parsed = json.loads(raw_text)
                        if parsed.get("diagnosis"):
                            print(f"[plant_doctor/analyze] Gemini Vision ({model_name}) diagnosed: {parsed.get('diagnosis')} ({parsed.get('confidence')}%)")

                            care_steps = parsed.get("care_steps", [])
                            if not care_steps or not isinstance(care_steps, list):
                                care_steps = [
                                    parsed.get("organic_remedy", "Spray cold-pressed neem oil solution."),
                                    parsed.get("prevention", "Ensure well-draining container soil."),
                                    "Isolate affected foliage to stop spread."
                                ]
                            # Cap to exactly 3 short treatment steps for speed & clarity
                            care_steps = care_steps[:3]

                            return {
                                "primary_cause": str(parsed.get("diagnosis")),
                                "confidence_pct": int(parsed.get("confidence", 90)),
                                "confidence_label": str(parsed.get("confidence_label", "High Confidence")),
                                "alternative_causes": parsed.get("alternative_causes", ["Micro-nutrient imbalance", "Moisture stress"]),
                                "follow_up_questions": parsed.get("follow_up_questions", ["Are other adjacent containers showing similar symptoms?", "How many hours of direct rooftop sun does this plant receive?"]),
                                "care_steps": care_steps,
                                "severity": str(parsed.get("severity", "Moderate")),
                                "organic_remedy": str(parsed.get("organic_remedy", "")),
                                "prevention": str(parsed.get("prevention", "")),
                                "engine": f"gemini_vision_{model_name}",
                                "disclaimer": f"Diagnosed by {model_name} Vision and grounded in BARI/DAE urban agronomy standards."
                            }
                except Exception as m_err:
                    print(f"[plant_doctor/analyze] Model {model_name} note: {m_err}")
                    # Rapid failover to next candidate model without sleeping
                    continue
        except Exception as e:
            print(f"[plant_doctor/analyze] Gemini Vision processing note (falling back to rule engine): {e}")

    # -----------------------------------------------------------------------
    # 2. Rule Engine Fallback (When no image or transient API fallback)
    # -----------------------------------------------------------------------
    symptom_text = " ".join(data.symptoms).lower()
    
    matched_rule = None
    for rule in RULES:
        if any(k in symptom_text for k in rule["keywords"]):
            matched_rule = rule
            break

    if not matched_rule:
        matched_rule = {
            "primary": "Environmental stress or micro-nutrient imbalance",
            "confidence": 72,
            "label": "Moderate",
            "alternatives": ["Seasonal temperature fluctuation", "Root compaction in small pot"],
            "questions": ["When did symptoms first appear?", "How many hours of direct sun does the plant receive?"],
            "steps": [
                "Examine soil aeration and ensure container is not root-bound.",
                "Apply balanced organic seaweed or vermicompost fertilizer.",
                "Ensure consistent morning watering regimen."
            ]
        }

    return {
        "primary_cause": matched_rule["primary"],
        "confidence_pct": matched_rule["confidence"],
        "confidence_label": matched_rule["label"],
        "alternative_causes": matched_rule["alternatives"],
        "follow_up_questions": matched_rule["questions"],
        "care_steps": matched_rule["steps"],
        "severity": "Moderate",
        "organic_remedy": matched_rule["steps"][1] if len(matched_rule["steps"]) > 1 else matched_rule["steps"][0],
        "prevention": matched_rule["steps"][-1],
        "engine": "rule_engine",
        "disclaimer": "This diagnosis is generated by RooftopGreen AI diagnostic heuristics. For commercial or severe agricultural crop loss, please consult a certified DAE (Department of Agricultural Extension) agronomist."
    }

# ---------------------------------------------------------------------------
# RAG Chatbot Endpoint: POST /api/plant-doctor/chat
# ---------------------------------------------------------------------------

@router.post("/chat")
def plant_doctor_chat(payload: PlantDoctorChatIn):
    query = (payload.message or payload.query or "").strip()
    if not query:
        return JSONResponse({"status": "error", "message": "Message cannot be empty"}, status_code=400)

    # 1. Resolve conversation history (last 4-6 messages)
    history_list = payload.history if payload.history else (payload.chat_history or [])

    # 2. Automatically include last diagnosed disease from leaf photo analysis
    diagnosis_ctx = payload.diagnosis_context or {}
    if payload.last_diagnosis:
        if not diagnosis_ctx.get("primary_cause"):
            diagnosis_ctx["primary_cause"] = payload.last_diagnosis
        if not diagnosis_ctx.get("disease"):
            diagnosis_ctx["disease"] = payload.last_diagnosis

    # Step A: Context-Aware RAG Retrieval
    retrieved_docs = retrieve_relevant_docs(
        query=query,
        diagnosis_context=diagnosis_ctx,
        history=history_list,
        top_k=3
    )

    sources_metadata = [
        {
            "id": d.get("id"),
            "title": d.get("title"),
            "crop": d.get("crop"),
            "source": d.get("source")
        }
        for d in retrieved_docs
    ]

    # Format retrieved knowledge context for LLM
    kb_context_blocks = []
    for i, doc in enumerate(retrieved_docs, start=1):
        kb_context_blocks.append(
            f"--- [Document {i}] ---\n"
            f"Title: {doc.get('title')}\n"
            f"Crop: {doc.get('crop')}\n"
            f"Symptoms & Signs: {doc.get('symptoms')}\n"
            f"Recommended Organic Treatment: {doc.get('treatment')}\n"
            f"Prevention: {doc.get('prevention')}\n"
            f"Authority Source: {doc.get('source')}"
        )
    kb_context_str = "\n\n".join(kb_context_blocks) if kb_context_blocks else "General Dhaka Rooftop Agronomy Guidelines (BARI & DAE Standards)"

    diag_context_str = "None provided"
    if diagnosis_ctx:
        diag_context_str = json.dumps(diagnosis_ctx, indent=2)

    # Step B: Construct Context-Aware RAG Prompt
    system_instruction = (
        "You are 'Plant Doctor AI', an urban agricultural specialist for rooftop gardens in Bangladesh, "
        "grounded in verified BARI (Bangladesh Agricultural Research Institute) and DAE (Department of Agricultural Extension) agronomic standards.\n\n"
        "RETRIEVED KNOWLEDGE BASE DOCUMENTS:\n"
        f"{kb_context_str}\n\n"
        "RECENT LEAF DIAGNOSIS CONTEXT:\n"
        f"{diag_context_str}\n\n"
        "INSTRUCTIONS:\n"
        "1. Answer the user's question directly, grounding your recommendations strictly in the retrieved documents above.\n"
        "2. For follow-up questions like 'why this happens?' or 'how much neem oil?', explicitly look at the CHAT HISTORY and RECENT LEAF DIAGNOSIS CONTEXT to identify the disease or crop being discussed. DO NOT repeat the entire initial diagnosis or give a canned generic introduction.\n"
        "3. When asked 'why this happens?', explain the biological pathogen/pest vectors, why Dhaka rooftop concrete heat/winds trigger it, and why the symptoms develop.\n"
        "4. Provide concrete, exact organic mixing ratios (e.g. 5ml neem oil + 2ml liquid soap per 1L water; 1 tsp baking soda per 1L; 10g Epsom salt per 1L) and watering times (early morning / late afternoon).\n"
        "5. Cite the relevant source in your explanation (e.g. '[BARI Rooftop Agriculture Manual]' or '[DAE Urban Gardening Guide]').\n"
        "6. Keep the response well-structured with clear bullet points. Do not make up unverified chemical pesticides."
    )

    history_str = ""
    if history_list:
        for turn in history_list[-6:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            history_str += f"{role.upper()}: {content}\n\n"

    final_prompt = f"{system_instruction}\n\nCHAT HISTORY:\n{history_str}\n\nCURRENT USER QUESTION: {query}\n\nEXPERT AGRONOMY ANSWER:"

    # Step C: Augmented Generation via Gemini (with instant RAG Fallback)
    candidate_models = ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-2.5-flash"]
    llm_reply = None
    used_model = None

    if genai_client:
        for model_name in candidate_models:
            try:
                response = genai_client.models.generate_content(
                    model=model_name,
                    contents=final_prompt,
                )
                if response and response.text:
                    llm_reply = response.text.strip()
                    used_model = model_name
                    print(f"[plant_doctor] RAG Chat generated successfully with {model_name}")
                    break
            except Exception as e:
                print(f"[plant_doctor] Gemini ({model_name}) note: {e}")

    # Fallback to smart knowledge base synthesis if LLM is unavailable / rate-limited / times out
    if not llm_reply:
        top_doc = retrieved_docs[0] if retrieved_docs else None
        llm_reply = synthesize_fallback_response(
            query=query,
            top_doc=top_doc,
            history=history_list,
            diagnosis_context=diagnosis_ctx
        )
        used_model = "rag_curated_knowledgebase"

        if not sources_metadata and top_doc:
            sources_metadata = [{
                "id": top_doc.get("id"),
                "title": top_doc.get("title"),
                "crop": top_doc.get("crop"),
                "source": top_doc.get("source")
            }]

    return {
        "status": "ok",
        "reply": llm_reply,
        "engine": used_model,
        "retrieved_sources": sources_metadata
    }
