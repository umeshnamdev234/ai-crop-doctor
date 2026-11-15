"""Directory models (experts, products, centres), file loading and deterministic ranking.

The AI only classifies the problem (crop, problem type, likely issues). Everything below is
plain, testable code, so recommendations are consistent and explainable.
"""
import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ProblemType = Literal["disease", "pest", "nutrient", "water", "weed", "soil", "general"]
PROBLEM_TYPES: list[str] = ["disease", "pest", "nutrient", "water", "weed", "soil", "general"]

# Which experts / products / centres fit each problem type (most relevant first)
EXPERTS_FOR = {
    "disease": ["Plant Pathologist", "Agronomist", "Horticulturist"],
    "pest": ["Entomologist", "Agronomist", "Horticulturist"],
    "nutrient": ["Soil Scientist", "Agronomist"],
    "water": ["Irrigation Specialist", "Agronomist"],
    "weed": ["Weed Scientist", "Agronomist"],
    "soil": ["Soil Scientist", "Agronomist", "Organic Farming Expert"],
    "general": ["Agronomist", "Agricultural Extension Officer", "Organic Farming Expert"],
}
PRODUCTS_FOR = {
    "disease": ["Fungicide", "Bactericide", "Bio-fungicide"],
    "pest": ["Insecticide", "Bio-insecticide", "Miticide"],
    "nutrient": ["Fertilizer", "Micronutrient"],
    "weed": ["Herbicide"],
    "soil": ["Soil Amendment", "Fertilizer", "Organic Manure"],
    "water": [],
    "general": [],
}
CENTRES_FOR = {
    "disease": ["Plant Clinic", "Krishi Vigyan Kendra", "Agri Input Shop"],
    "pest": ["Plant Clinic", "Krishi Vigyan Kendra", "Agri Input Shop"],
    "nutrient": ["Soil Testing Lab", "Krishi Vigyan Kendra", "Agri Input Shop"],
    "soil": ["Soil Testing Lab", "Krishi Vigyan Kendra"],
    "water": ["Krishi Vigyan Kendra"],
    "weed": ["Krishi Vigyan Kendra", "Agri Input Shop"],
    "general": ["Krishi Vigyan Kendra", "Plant Clinic"],
}


# ---------- models ----------
class Expert(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1)
    expert_type: str = Field(..., min_length=1)          # e.g. Plant Pathologist
    crops: list[str] = Field(default_factory=list)       # crops they specialise in (empty = all)
    expertise: list[str] = Field(default_factory=list)   # problems they handle, e.g. "early blight"
    organisation: str = ""
    qualifications: str = ""
    experience_years: int = Field(0, ge=0, le=80)
    languages: list[str] = Field(default_factory=list)
    state: str = ""
    district: str = ""
    rating: float = Field(0.0, ge=0, le=5)
    review_count: int = Field(0, ge=0)
    fee: int = Field(0, ge=0)                            # 0 = free (government extension)
    phone_consult: bool = False
    field_visit: bool = False
    available_days: list[str] = Field(default_factory=list)


class Product(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1)                 # generic name, e.g. "Mancozeb 75% WP"
    category: str = Field(..., min_length=1)             # Fungicide, Insecticide, Fertilizer, ...
    active_ingredient: str = ""
    targets: list[str] = Field(default_factory=list)     # problems it treats
    crops: list[str] = Field(default_factory=list)       # crops it is used on (empty = many)
    organic: bool = False
    dose: str = ""
    safety_notes: str = ""
    waiting_period_days: Optional[int] = Field(None, ge=0)
    price_inr: Optional[int] = Field(None, ge=0)
    unit: str = ""


class Centre(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1)
    centre_type: str = Field(..., min_length=1)          # Krishi Vigyan Kendra, Soil Testing Lab, ...
    services: list[str] = Field(default_factory=list)
    state: str = ""
    district: str = ""
    address: str = ""
    languages: list[str] = Field(default_factory=list)
    open_days: list[str] = Field(default_factory=list)
    free_service: bool = False


class Ranked(BaseModel):
    score: float
    match_reasons: list[str]


class RankedExpert(Expert, Ranked):
    next_available: Optional[str] = None


class RankedProduct(Product, Ranked):
    pass


class RankedCentre(Centre, Ranked):
    next_open: Optional[str] = None


class Location(BaseModel):
    state: Optional[str] = None
    district: Optional[str] = None


# ---------- helpers ----------
def _norm(s: str) -> str:
    return s.strip().lower()


def _overlap(needles: list[str], hay: list[str]) -> Optional[str]:
    """First needle that matches (substring either way) any item in hay; ignores very short words."""
    hay_n = [_norm(h) for h in hay]
    for n in needles:
        nn = _norm(n)
        if len(nn) < 3:
            continue
        if any(nn in h or h in nn for h in hay_n if len(h) >= 3):
            return n
    return None


def next_available(days: list[str], today: date) -> tuple[Optional[str], Optional[int]]:
    wanted = {d[:3].title() for d in days}
    for i in range(7):
        day = today + timedelta(days=i)
        if DAYS[day.weekday()] in wanted:
            label = "Today" if i == 0 else "Tomorrow" if i == 1 else day.strftime("%a, %d %b")
            return label, i
    return None, None


def _location_score(state: str, district: str, loc: Location, remote_ok: bool, reasons: list[str]) -> float:
    if loc.district and _norm(district) == _norm(loc.district):
        reasons.append(f"In {district}")
        return 0.4
    if loc.state and _norm(state) == _norm(loc.state):
        reasons.append(f"In {state}")
        return 0.2
    if (loc.district or loc.state) and remote_ok:
        reasons.append("Phone consultation")
        return 0.05
    return -0.3 if (loc.district or loc.state) else 0.0


# ---------- ranking ----------
def rank_experts(experts: list[Expert], problem_type: str, crop: str, issues: list[str], loc: Location,
                 language: Optional[str] = None, limit: int = 4, today: Optional[date] = None) -> list[RankedExpert]:
    wanted = EXPERTS_FOR.get(problem_type, EXPERTS_FOR["general"])
    weights = {t: w for t, w in zip(wanted, [1.0, 0.7, 0.5])}
    today = today or date.today()
    out = []
    for e in experts:
        w = weights.get(e.expert_type)
        if w is None:
            continue
        reasons, score = [e.expert_type], w
        if crop and e.crops and _overlap([crop], e.crops):
            score += 0.3
            reasons.append(f"{crop.title()} specialist")
        hit = _overlap(issues, e.expertise)
        if hit:
            score += 0.3
            reasons.append(f"Handles {hit}")
        score += e.rating / 5 * 0.25 + min(e.experience_years, 30) / 30 * 0.15
        score += _location_score(e.state, e.district, loc, e.phone_consult, reasons)
        if language and any(_norm(lang) == _norm(language) for lang in e.languages):
            score += 0.1
            reasons.append(f"Speaks {language}")
        if e.fee == 0:
            score += 0.05
            reasons.append("Free advice")
        label, in_days = next_available(e.available_days, today)
        if in_days == 0:
            score += 0.05
            reasons.append("Available today")
        out.append(RankedExpert(**e.model_dump(), score=round(score, 3), match_reasons=reasons, next_available=label))
    out.sort(key=lambda r: (-r.score, -r.rating))
    return out[:limit]


def rank_products(products: list[Product], problem_type: str, crop: str, issues: list[str],
                  organic_only: bool = False, limit: int = 4) -> list[RankedProduct]:
    categories = PRODUCTS_FOR.get(problem_type, [])
    if not categories or not issues:
        return []  # never suggest chemicals without a specific suspected problem
    out = []
    for p in products:
        if p.category not in categories or (organic_only and not p.organic):
            continue
        hit = _overlap(issues, p.targets)
        if not hit:
            continue  # only suggest products whose label targets the suspected problem
        reasons, score = [p.category], 1.0
        if hit:
            score += 0.6
            reasons.append(f"For {hit}")
        if crop and p.crops:
            if _overlap([crop], p.crops):
                score += 0.3
                reasons.append(f"Used on {crop}")
            else:
                score -= 0.4
        if p.organic:
            score += 0.15
            reasons.append("Organic / bio")
        out.append(RankedProduct(**p.model_dump(), score=round(score, 3), match_reasons=reasons))
    out.sort(key=lambda r: (-r.score, r.price_inr or 0))
    return out[:limit]


def rank_centres(centres: list[Centre], problem_type: str, loc: Location, language: Optional[str] = None,
                 limit: int = 3, today: Optional[date] = None) -> list[RankedCentre]:
    wanted = CENTRES_FOR.get(problem_type, CENTRES_FOR["general"])
    weights = {t: w for t, w in zip(wanted, [1.0, 0.7, 0.5])}
    today = today or date.today()
    out = []
    for c in centres:
        w = weights.get(c.centre_type)
        if w is None:
            continue
        reasons, score = [c.centre_type], w
        score += _location_score(c.state, c.district, loc, False, reasons) * 1.5  # distance matters most here
        if language and any(_norm(lang) == _norm(language) for lang in c.languages):
            score += 0.1
            reasons.append(f"Speaks {language}")
        if c.free_service:
            score += 0.05
            reasons.append("Free service")
        label, in_days = next_available(c.open_days, today)
        if in_days == 0:
            score += 0.05
            reasons.append("Open today")
        out.append(RankedCentre(**c.model_dump(), score=round(score, 3), match_reasons=reasons, next_open=label))
    out.sort(key=lambda r: -r.score)
    return out[:limit]


# ---------- file loading (imports) ----------
KIND_MODELS = {"experts": Expert, "products": Product, "centres": Centre}
_LIST_FIELDS = {"crops", "expertise", "languages", "available_days", "targets", "services", "open_days"}
_BOOL_FIELDS = {"phone_consult", "field_visit", "organic", "free_service"}
_NUM_FIELDS = {"experience_years", "rating", "review_count", "fee", "waiting_period_days", "price_inr"}


def _from_csv(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            row: dict = {k.strip(): (v or "").strip() for k, v in r.items() if k}
            for k in _LIST_FIELDS & row.keys():
                row[k] = [x.strip() for x in row[k].split(";") if x.strip()]
            for k in _BOOL_FIELDS & row.keys():
                row[k] = str(row[k]).lower() in ("1", "true", "yes", "y")
            for k in _NUM_FIELDS & row.keys():
                if row[k] == "":
                    row.pop(k)
            rows.append(row)
    return rows


def load_file(kind: str, file: str | Path) -> list[BaseModel]:
    """Loads experts / products / centres from CSV, a JSON list, or JSON {"<kind>": [...]}."""
    model = KIND_MODELS[kind]
    path = Path(file)
    if path.suffix.lower() == ".csv":
        raw = _from_csv(path)
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data[kind] if isinstance(data, dict) else data
    return [model.model_validate(r) for r in raw]
