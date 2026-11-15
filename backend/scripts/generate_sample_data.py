"""Generates SAMPLE directory data for development: data/sample_directory.json

    .venv/bin/python scripts/generate_sample_data.py

- experts and centres are FICTIONAL (names, places and organisations are made up)
- products use real generic active ingredients with commonly published uses, but doses
  and prices are indicative only. Always verify with the product label and local agriculture
  officers before giving real advice.
"""
import json
import random
from pathlib import Path

random.seed(7)
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

LOCATIONS = {
    "Maharashtra": (["Pune", "Nashik", "Nagpur", "Aurangabad"], ["Marathi", "Hindi"]),
    "Madhya Pradesh": (["Indore", "Bhopal", "Jabalpur", "Ujjain"], ["Hindi"]),
    "Uttar Pradesh": (["Lucknow", "Varanasi", "Meerut", "Agra"], ["Hindi"]),
    "Punjab": (["Ludhiana", "Amritsar", "Bathinda"], ["Punjabi", "Hindi"]),
    "Rajasthan": (["Jaipur", "Kota", "Jodhpur"], ["Hindi"]),
    "Karnataka": (["Dharwad", "Mysuru", "Belagavi"], ["Kannada", "Hindi"]),
}

EXPERT_TYPES = {
    "Plant Pathologist": (24, ["early blight", "late blight", "leaf spot", "powdery mildew", "downy mildew", "rust", "blast",
                               "bacterial blight", "wilt", "root rot", "leaf curl virus", "mosaic virus", "anthracnose"]),
    "Entomologist": (22, ["aphids", "whitefly", "thrips", "jassids", "fruit borer", "stem borer", "fall armyworm",
                          "pink bollworm", "mites", "brown plant hopper", "termites", "pod borer"]),
    "Soil Scientist": (18, ["nitrogen deficiency", "phosphorus deficiency", "potassium deficiency", "zinc deficiency",
                            "iron deficiency", "boron deficiency", "soil testing", "saline soil", "acidic soil"]),
    "Agronomist": (28, ["crop planning", "sowing", "fertilizer schedule", "yield improvement", "intercropping", "seed selection"]),
    "Horticulturist": (14, ["fruit drop", "flower drop", "pruning", "orchard management", "nursery", "fruit cracking"]),
    "Irrigation Specialist": (10, ["drip irrigation", "sprinkler", "waterlogging", "drought", "irrigation schedule"]),
    "Weed Scientist": (10, ["weed control", "phalaris minor", "parthenium", "herbicide selection", "broadleaf weeds"]),
    "Organic Farming Expert": (14, ["organic farming", "vermicompost", "jeevamrut", "bio-pesticides", "natural farming"]),
    "Agricultural Extension Officer": (10, ["government schemes", "crop insurance", "soil health card", "general advice"]),
}
CROPS = ["wheat", "rice", "cotton", "soybean", "maize", "tomato", "potato", "onion", "chilli", "sugarcane",
         "chickpea", "mustard", "groundnut", "grapes", "banana", "brinjal"]
ORGS = ["Sample KVK", "Sample State Agricultural University", "Sample Farmer Producer Organisation",
        "Independent consultant", "Sample Agri Startup", "Sample District Agriculture Office"]
FIRST = ["Ramesh", "Sunita", "Mahesh", "Kavita", "Suresh", "Anita", "Rajesh", "Pooja", "Vijay", "Rekha", "Anil", "Seema",
         "Prakash", "Meena", "Sanjay", "Neha", "Gurpreet", "Harjit", "Basavaraj", "Lakshmi", "Dinesh", "Asha", "Mohan", "Kiran"]
LAST = ["Patil", "Pawar", "Sharma", "Yadav", "Verma", "Singh", "Chauhan", "Deshmukh", "Jadhav", "Gill", "Sandhu",
        "Gowda", "Hegde", "Mishra", "Tiwari", "Choudhary", "Meena", "Rathore", "Kale", "Shinde"]
QUAL = {"Plant Pathologist": "M.Sc. (Plant Pathology)", "Entomologist": "M.Sc. (Entomology)", "Soil Scientist": "M.Sc. (Soil Science)",
        "Agronomist": "M.Sc. (Agronomy)", "Horticulturist": "M.Sc. (Horticulture)", "Irrigation Specialist": "B.Tech (Agri Engg.)",
        "Weed Scientist": "Ph.D. (Agronomy)", "Organic Farming Expert": "B.Sc. (Agriculture)",
        "Agricultural Extension Officer": "B.Sc. (Agriculture)"}

experts = []
n = 0
for etype, (count, expertise) in EXPERT_TYPES.items():
    for _ in range(count):
        n += 1
        state = random.choice(list(LOCATIONS))
        districts, langs = LOCATIONS[state]
        org = random.choice(ORGS)
        govt = org.startswith("Sample KVK") or "University" in org or "Office" in org
        exp = random.randint(2, 30)
        experts.append({
            "id": f"E{n:03d}",
            "name": f"{random.choice(FIRST)} {random.choice(LAST)} (sample)",
            "expert_type": etype,
            "crops": random.sample(CROPS, k=random.randint(2, 5)),
            "expertise": random.sample(expertise, k=min(len(expertise), random.randint(3, 6))),
            "organisation": f"{org}, {random.choice(districts)}" if org != "Independent consultant" else org,
            "qualifications": QUAL[etype],
            "experience_years": exp,
            "languages": random.sample(langs, k=len(langs)) + (["English"] if random.random() < 0.6 else []),
            "state": state,
            "district": random.choice(districts),
            "rating": round(min(5.0, random.uniform(3.7, 4.6) + exp / 120), 1),
            "review_count": random.randint(5, 400),
            "fee": 0 if govt else random.choice([100, 200, 300, 500]),
            "phone_consult": random.random() < 0.7,
            "field_visit": random.random() < 0.5,
            "available_days": sorted(random.sample(DAYS[:6], k=random.randint(3, 6)), key=DAYS.index),
        })

# (name, category, active ingredient, targets, crops, organic, dose, waiting days, price, unit)
PRODUCTS = [
    # --- fungicides / bactericides ---
    ("Mancozeb 75% WP", "Fungicide", "Mancozeb", ["early blight", "late blight", "leaf spot", "downy mildew", "rust", "anthracnose"], ["tomato", "potato", "chilli", "grapes", "onion"], False, "2–2.5 g per litre of water", 7, 450, "500 g"),
    ("Copper Oxychloride 50% WP", "Fungicide", "Copper oxychloride", ["late blight", "leaf spot", "bacterial blight", "bacterial leaf spot", "canker", "downy mildew"], ["tomato", "potato", "chilli", "grapes", "banana"], False, "2.5–3 g per litre of water", 7, 400, "500 g"),
    ("Metalaxyl 8% + Mancozeb 64% WP", "Fungicide", "Metalaxyl + Mancozeb", ["late blight", "downy mildew", "damping off", "root rot"], ["potato", "tomato", "grapes", "onion"], False, "2.5 g per litre of water", 7, 650, "500 g"),
    ("Carbendazim 50% WP", "Fungicide", "Carbendazim", ["powdery mildew", "anthracnose", "leaf spot", "wilt", "root rot"], ["chilli", "wheat", "rice", "groundnut"], False, "1 g per litre of water", 15, 350, "250 g"),
    ("Hexaconazole 5% EC", "Fungicide", "Hexaconazole", ["powdery mildew", "sheath blight", "rust", "leaf spot"], ["rice", "grapes", "chilli", "groundnut"], False, "2 ml per litre of water", 15, 380, "500 ml"),
    ("Propiconazole 25% EC", "Fungicide", "Propiconazole", ["rust", "sheath blight", "leaf spot", "powdery mildew"], ["wheat", "rice", "banana"], False, "1 ml per litre of water", 30, 520, "250 ml"),
    ("Tricyclazole 75% WP", "Fungicide", "Tricyclazole", ["blast", "rice blast", "neck blast"], ["rice"], False, "0.6 g per litre of water", 30, 420, "120 g"),
    ("Azoxystrobin 23% SC", "Fungicide", "Azoxystrobin", ["early blight", "late blight", "powdery mildew", "downy mildew", "anthracnose"], ["tomato", "potato", "chilli", "grapes"], False, "1 ml per litre of water", 5, 900, "250 ml"),
    ("Wettable Sulphur 80% WG", "Fungicide", "Sulphur", ["powdery mildew", "mites"], ["grapes", "chilli", "mustard"], False, "2–3 g per litre of water", 5, 250, "1 kg"),
    ("Trichoderma viride 1% WP", "Bio-fungicide", "Trichoderma viride", ["wilt", "root rot", "damping off", "collar rot"], [], True, "Seed: 5–10 g per kg; soil: 2.5 kg mixed in 100 kg compost per acre", 0, 180, "1 kg"),
    ("Pseudomonas fluorescens 1% WP", "Bio-fungicide", "Pseudomonas fluorescens", ["blast", "bacterial blight", "wilt", "leaf spot", "root rot"], ["rice", "tomato", "banana"], True, "10 g per litre of water; seed treatment 10 g per kg", 0, 200, "1 kg"),
    # --- insecticides / miticides ---
    ("Imidacloprid 17.8% SL", "Insecticide", "Imidacloprid", ["aphids", "jassids", "whitefly", "thrips", "brown plant hopper"], ["cotton", "chilli", "tomato", "rice", "brinjal"], False, "0.3–0.5 ml per litre of water", 7, 380, "250 ml"),
    ("Thiamethoxam 25% WG", "Insecticide", "Thiamethoxam", ["aphids", "whitefly", "jassids", "brown plant hopper", "thrips"], ["cotton", "rice", "tomato", "potato"], False, "0.3–0.5 g per litre of water", 7, 420, "100 g"),
    ("Emamectin Benzoate 5% SG", "Insecticide", "Emamectin benzoate", ["fruit borer", "fall armyworm", "diamondback moth", "pod borer", "shoot and fruit borer"], ["tomato", "chilli", "brinjal", "maize", "chickpea"], False, "0.4 g per litre of water", 5, 450, "100 g"),
    ("Chlorantraniliprole 18.5% SC", "Insecticide", "Chlorantraniliprole", ["stem borer", "fruit borer", "fall armyworm", "pod borer", "leaf folder"], ["rice", "maize", "tomato", "sugarcane", "chickpea"], False, "0.3 ml per litre of water", 3, 1100, "150 ml"),
    ("Spinosad 45% SC", "Insecticide", "Spinosad", ["thrips", "fruit borer", "diamondback moth", "leaf miner"], ["chilli", "onion", "tomato", "brinjal"], False, "0.3 ml per litre of water", 3, 1300, "75 ml"),
    ("Fipronil 5% SC", "Insecticide", "Fipronil", ["stem borer", "thrips", "termites", "leaf folder"], ["rice", "chilli", "sugarcane"], False, "1.5–2 ml per litre of water", 15, 350, "250 ml"),
    ("Lambda-cyhalothrin 5% EC", "Insecticide", "Lambda-cyhalothrin", ["pod borer", "fruit borer", "bollworm", "pink bollworm", "jassids"], ["cotton", "chickpea", "tomato", "brinjal"], False, "1 ml per litre of water", 7, 320, "250 ml"),
    ("Diafenthiuron 50% WP", "Insecticide", "Diafenthiuron", ["whitefly", "mites", "jassids"], ["cotton", "chilli", "brinjal"], False, "1 g per litre of water", 7, 480, "250 g"),
    ("Spiromesifen 22.9% SC", "Miticide", "Spiromesifen", ["mites", "red spider mite", "whitefly"], ["chilli", "tomato", "brinjal", "cotton"], False, "0.8 ml per litre of water", 7, 1200, "100 ml"),
    ("Buprofezin 25% SC", "Insecticide", "Buprofezin", ["brown plant hopper", "whitefly", "mealybug"], ["rice", "cotton"], False, "1.6 ml per litre of water", 20, 450, "250 ml"),
    ("Neem Oil 1500 ppm (Azadirachtin)", "Bio-insecticide", "Azadirachtin", ["aphids", "whitefly", "jassids", "thrips", "mites", "leaf miner"], [], True, "3–5 ml per litre of water with a few drops of liquid soap", 0, 300, "1 litre"),
    ("Beauveria bassiana 1% WP", "Bio-insecticide", "Beauveria bassiana", ["whitefly", "stem borer", "fruit borer", "termites", "aphids"], [], True, "5 g per litre of water, spray in the evening", 0, 220, "1 kg"),
    ("Bacillus thuringiensis var. kurstaki", "Bio-insecticide", "Bacillus thuringiensis", ["fruit borer", "diamondback moth", "fall armyworm", "pod borer", "caterpillar"], [], True, "1–2 g per litre of water", 0, 350, "500 g"),
    ("Pheromone Trap + Lure (Helicoverpa)", "Bio-insecticide", "Pheromone lure", ["fruit borer", "pod borer", "bollworm", "pink bollworm"], ["tomato", "chickpea", "cotton"], True, "5 traps per acre; change lure every 3 weeks", 0, 150, "1 trap"),
    # --- herbicides ---
    ("Pendimethalin 30% EC", "Herbicide", "Pendimethalin", ["weed control", "annual grasses", "broadleaf weeds"], ["soybean", "cotton", "onion", "wheat", "chickpea"], False, "1–1.3 litre per acre in 200 litres of water, pre-emergence (within 3 days of sowing)", None, 550, "1 litre"),
    ("Metsulfuron Methyl 20% WP", "Herbicide", "Metsulfuron methyl", ["broadleaf weeds", "weed control"], ["wheat"], False, "8 g per acre in 150 litres of water, 30–35 days after sowing", None, 150, "8 g"),
    ("Clodinafop-propargyl 15% WP", "Herbicide", "Clodinafop-propargyl", ["phalaris minor", "wild oat", "grassy weeds", "weed control"], ["wheat"], False, "160 g per acre in 150 litres of water, 30–35 days after sowing", None, 650, "160 g"),
    ("Bispyribac Sodium 10% SC", "Herbicide", "Bispyribac sodium", ["grassy weeds", "sedges", "broadleaf weeds", "weed control"], ["rice"], False, "80–100 ml per acre in 150 litres of water, 15–25 days after sowing/transplanting", None, 500, "100 ml"),
    ("Atrazine 50% WP", "Herbicide", "Atrazine", ["broadleaf weeds", "annual grasses", "weed control"], ["maize", "sugarcane"], False, "400–500 g per acre in 200 litres of water, pre-emergence", None, 250, "500 g"),
    # --- fertilizers / micronutrients ---
    ("Urea (46% N)", "Fertilizer", "Nitrogen", ["nitrogen deficiency", "yellowing of older leaves", "stunted growth"], [], False, "As per soil test; split doses. Foliar: 1–2% solution (10–20 g per litre)", None, 270, "45 kg"),
    ("DAP (18-46-0)", "Fertilizer", "Nitrogen + Phosphorus", ["phosphorus deficiency", "purple leaves", "poor root growth"], [], False, "As per soil test, usually at sowing (basal)", None, 1350, "50 kg"),
    ("Muriate of Potash (60% K2O)", "Fertilizer", "Potassium", ["potassium deficiency", "leaf edge scorching", "weak stems"], [], False, "As per soil test, usually basal", None, 1700, "50 kg"),
    ("NPK 19:19:19 (water soluble)", "Fertilizer", "N + P + K", ["nutrient deficiency", "slow growth", "nitrogen deficiency", "potassium deficiency"], [], False, "Foliar: 5 g per litre of water", None, 150, "1 kg"),
    ("Zinc Sulphate (21% Zn)", "Micronutrient", "Zinc", ["zinc deficiency", "khaira disease", "small leaves", "interveinal chlorosis"], ["rice", "wheat", "maize"], False, "Soil: 10 kg per acre; foliar: 5 g per litre (with 2.5 g lime)", None, 120, "1 kg"),
    ("Ferrous Sulphate (19% Fe)", "Micronutrient", "Iron", ["iron deficiency", "interveinal chlorosis", "yellowing of young leaves"], [], False, "Foliar: 5 g per litre of water", None, 80, "1 kg"),
    ("Boron 20% (Disodium Octaborate)", "Micronutrient", "Boron", ["boron deficiency", "fruit cracking", "flower drop", "hollow stem"], ["tomato", "grapes", "mustard", "groundnut"], False, "Foliar: 1 g per litre of water", None, 180, "500 g"),
    ("Magnesium Sulphate", "Micronutrient", "Magnesium", ["magnesium deficiency", "interveinal chlorosis of older leaves"], [], False, "Foliar: 5–10 g per litre of water", None, 90, "1 kg"),
    ("Calcium Nitrate", "Fertilizer", "Calcium + Nitrogen", ["calcium deficiency", "blossom end rot", "tip burn"], ["tomato", "chilli", "grapes"], False, "Foliar: 5 g per litre of water", None, 160, "1 kg"),
    # --- soil amendments / organic ---
    ("Vermicompost", "Organic Manure", "Organic matter", ["soil health", "low organic carbon", "poor soil structure", "nutrient deficiency"], [], True, "1–2 tonnes per acre before sowing", None, 600, "50 kg"),
    ("Gypsum (Agricultural grade)", "Soil Amendment", "Calcium sulphate", ["sodic soil", "alkaline soil", "saline soil", "calcium deficiency"], ["groundnut", "mustard", "wheat"], False, "As per soil test (often 200–400 kg per acre)", None, 300, "50 kg"),
    ("Agricultural Lime", "Soil Amendment", "Calcium carbonate", ["acidic soil", "low ph"], [], False, "As per soil test lime requirement", None, 250, "50 kg"),
]
products = [
    {"id": f"P{i + 1:03d}", "name": p[0], "category": p[1], "active_ingredient": p[2], "targets": p[3], "crops": p[4],
     "organic": p[5], "dose": p[6] + " (SAMPLE: verify on the product label)",
     "safety_notes": ("Bio-input: still wear gloves and avoid mixing with chemical fungicides/insecticides."
                      if p[5] else "Wear gloves, mask and full sleeves. Do not spray in strong wind or before rain. Keep away from children, animals and water sources."),
     "waiting_period_days": p[7], "price_inr": p[8], "unit": p[9]}
    for i, p in enumerate(PRODUCTS)
]

CENTRE_TYPES = {
    "Krishi Vigyan Kendra": (["crop advisory", "training", "seed and planting material", "plant diagnosis", "demonstrations"], True),
    "Soil Testing Lab": (["soil testing", "soil health card", "water testing", "fertilizer recommendation"], True),
    "Plant Clinic": (["plant diagnosis", "pest identification", "disease identification", "spray advice"], True),
    "Agri Input Shop": (["seeds", "fertilizers", "pesticides", "bio-inputs", "sprayers"], False),
}
centres = []
n = 0
for state, (districts, langs) in LOCATIONS.items():
    for district in districts:
        for ctype, (services, free) in CENTRE_TYPES.items():
            if ctype != "Krishi Vigyan Kendra" and random.random() < 0.35:
                continue
            n += 1
            centres.append({
                "id": f"C{n:03d}",
                "name": f"{ctype}, {district} (sample)",
                "centre_type": ctype,
                "services": random.sample(services, k=random.randint(2, len(services))),
                "state": state,
                "district": district,
                "address": f"Sample address, {district}, {state}",
                "languages": langs + ["English"],
                "open_days": DAYS[:6] if ctype != "Agri Input Shop" else DAYS,
                "free_service": free,
            })

out = Path(__file__).resolve().parent.parent / "data" / "sample_directory.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({
    "_note": "SAMPLE data for development. Experts and centres are fictional; product doses/prices are indicative only.",
    "experts": experts, "products": products, "centres": centres,
}, indent=1, ensure_ascii=False))
print(f"Wrote {len(experts)} experts, {len(products)} products, {len(centres)} centres to {out}")
