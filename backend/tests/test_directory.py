"""Tests for ranking, safety and keyword triage (no model or database needed)."""
from datetime import date

import pytest

from app.directory import Centre, Expert, Location, Product, load_file, rank_centres, rank_experts, rank_products
from app.safety import EMERGENCY_NOTICE, EMERGENCY_NOTICE_HI, detect_emergency, emergency_notice
from app.triage import detect_crop, keyword_triage

MONDAY = date(2026, 11, 16)

EXPERTS = [Expert(**e) for e in [
    {"id": "1", "name": "A", "expert_type": "Plant Pathologist", "crops": ["tomato"], "expertise": ["early blight"],
     "state": "Maharashtra", "district": "Pune", "rating": 4.0, "languages": ["Marathi", "Hindi"], "available_days": ["Mon"]},
    {"id": "2", "name": "B", "expert_type": "Plant Pathologist", "crops": ["wheat"], "expertise": ["rust"],
     "state": "Punjab", "district": "Ludhiana", "rating": 4.9, "experience_years": 25, "phone_consult": True},
    {"id": "3", "name": "C", "expert_type": "Entomologist", "crops": ["tomato"], "expertise": ["fruit borer"],
     "state": "Maharashtra", "district": "Pune", "rating": 5.0},
    {"id": "4", "name": "D", "expert_type": "Agronomist", "state": "Maharashtra", "district": "Nashik", "rating": 4.2, "fee": 0},
]]
PRODUCTS = [Product(**p) for p in [
    {"id": "p1", "name": "Mancozeb 75% WP", "category": "Fungicide", "targets": ["early blight", "late blight"], "crops": ["tomato", "potato"]},
    {"id": "p2", "name": "Propiconazole", "category": "Fungicide", "targets": ["rust"], "crops": ["wheat"]},
    {"id": "p3", "name": "Trichoderma", "category": "Bio-fungicide", "targets": ["wilt", "early blight"], "organic": True},
    {"id": "p4", "name": "Imidacloprid", "category": "Insecticide", "targets": ["aphids"]},
]]
CENTRES = [Centre(**c) for c in [
    {"id": "c1", "name": "KVK Pune", "centre_type": "Krishi Vigyan Kendra", "state": "Maharashtra", "district": "Pune", "open_days": ["Mon"]},
    {"id": "c2", "name": "Lab Pune", "centre_type": "Soil Testing Lab", "state": "Maharashtra", "district": "Pune"},
    {"id": "c3", "name": "Clinic Ludhiana", "centre_type": "Plant Clinic", "state": "Punjab", "district": "Ludhiana"},
]]
PUNE = Location(state="Maharashtra", district="Pune")


# ---------- experts ----------
def test_disease_goes_to_plant_pathologist_first():
    ranked = rank_experts(EXPERTS, "disease", "tomato", ["early blight"], PUNE, today=MONDAY)
    assert ranked[0].id == "1"
    assert {"Tomato specialist", "Handles early blight", "In Pune", "Available today"} <= set(ranked[0].match_reasons)


def test_pest_goes_to_entomologist():
    assert rank_experts(EXPERTS, "pest", "tomato", ["fruit borer"], PUNE, today=MONDAY)[0].expert_type == "Entomologist"


def test_unrelated_expert_types_are_excluded():
    assert all(e.expert_type in ("Plant Pathologist", "Agronomist", "Horticulturist")
               for e in rank_experts(EXPERTS, "disease", "", [], Location(), today=MONDAY))


def test_language_bonus():
    ranked = rank_experts(EXPERTS, "disease", "", [], Location(), language="Marathi", today=MONDAY)
    assert "Speaks Marathi" in ranked[[e.id for e in ranked].index("1")].match_reasons


# ---------- products ----------
def test_products_must_target_the_issue():
    ranked = rank_products(PRODUCTS, "disease", "tomato", ["early blight"])
    assert [p.id for p in ranked] == ["p1", "p3"] or [p.id for p in ranked] == ["p3", "p1"]
    assert "p2" not in [p.id for p in ranked]  # rust product is not suggested for early blight


def test_organic_only():
    assert [p.id for p in rank_products(PRODUCTS, "disease", "tomato", ["early blight"], organic_only=True)] == ["p3"]


def test_no_products_without_a_specific_diagnosis():
    assert rank_products(PRODUCTS, "disease", "tomato", []) == []


def test_no_products_for_water_problems():
    assert rank_products(PRODUCTS, "water", "tomato", ["drought"]) == []


# ---------- centres ----------
def test_soil_problems_prefer_soil_lab_nearby():
    ranked = rank_centres(CENTRES, "soil", PUNE, today=MONDAY)
    assert ranked[0].id == "c2"


def test_nearby_centre_beats_far_one():
    ranked = rank_centres(CENTRES, "disease", PUNE, today=MONDAY)
    assert ranked[0].district == "Pune"


# ---------- safety ----------
@pytest.mark.parametrize("text", [
    "my brother drank pesticide",
    "he accidentally swallowed some insecticide",
    "felt dizzy and vomiting after spraying",
    "उसने कीटनाशक पी लिया",
    "मेरे पिताजी ने ज़हर खा लिया",
    "usne dawa pi li",
])
def test_emergency_detected(text):
    assert detect_emergency(text)


@pytest.mark.parametrize("text", [
    "which pesticide should I spray on tomato",
    "टमाटर पर कौन सी दवा डालें",
    "how much urea for wheat",
])
def test_normal_questions_not_flagged(text):
    assert not detect_emergency(text)


# ---------- keyword triage ----------
@pytest.mark.parametrize("text,ptype,crop", [
    ("brown spots on my tomato leaves", "disease", "tomato"),
    ("गेहूं की पत्तियां पीली हो रही हैं", "nutrient", "wheat"),
    ("caterpillars eating maize leaves", "pest", "maize"),
    ("धान में खरपतवार बहुत है", "weed", "rice"),
    ("when should I sow", "general", ""),
])
def test_keyword_triage(text, ptype, crop):
    assert keyword_triage(text) == (ptype, crop)


def test_detect_crop_hindi():
    assert detect_crop("मेरे टमाटर के पौधे") == "tomato"


def test_csv_loading(tmp_path):
    p = tmp_path / "experts.csv"
    p.write_text("id,name,expert_type,crops,languages,phone_consult,rating\nX1,Test,Agronomist,wheat;rice,Hindi;English,yes,4.5\n")
    e = load_file("experts", p)[0]
    assert e.crops == ["wheat", "rice"] and e.phone_consult is True and e.rating == 4.5


def test_emergency_notice_language():
    assert emergency_notice("उसने कीटनाशक पी लिया") == EMERGENCY_NOTICE_HI
    assert emergency_notice("he drank pesticide") == EMERGENCY_NOTICE
    assert emergency_notice("he drank pesticide", "hi") == EMERGENCY_NOTICE_HI
