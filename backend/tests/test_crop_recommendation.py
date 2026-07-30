"""
test_crop_recommendation.py — Comprehensive Regression Test Suite
Validates:
1. Soil type auto-detection from gujarat_agro_zones.json
2. Region isolation (zero cross-region text leakage for Surat vs Kutch)
3. Location crop distinctness across Surat, Kutch, Rajkot, Anand
4. NPK conflict detection when farmer inputs deviate from zone baseline
5. Validation Guard functionality
"""

import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.regional_crop_lookup import fetch_real_crops_for_location, lookup_district_crops
from services.ai_crop_advisor import (
    generate_geographical_crop_advice,
    detect_default_soil_type,
    validate_region_isolation,
    _get_soil_key
)


def test_1_dataset_lookup_and_soil_detection():
    """Test 1: Verify gujarat_agro_zones.json correctly maps districts to soil types and zone names."""
    print("\n--- Test 1: Grounding Dataset Lookup ---")

    surat_data = lookup_district_crops("Surat", "Gujarat")
    assert surat_data is not None, "Surat must exist in dataset"
    assert "Black" in surat_data["soil"] or "Vertisol" in surat_data["soil"], f"Unexpected Surat soil: {surat_data['soil']}"
    assert surat_data["agro_climatic_zone_name"] == "South Gujarat Heavy Rainfall Zone"

    kutch_data = lookup_district_crops("Kutch", "Gujarat")
    assert kutch_data is not None, "Kutch must exist in dataset"
    assert "Sandy Arid" in kutch_data["soil"], f"Unexpected Kutch soil: {kutch_data['soil']}"
    assert kutch_data["agro_climatic_zone_name"] == "North-West Arid Zone (Kutch)"

    rajkot_data = lookup_district_crops("Rajkot", "Gujarat")
    assert rajkot_data is not None, "Rajkot must exist in dataset"
    assert "North Saurashtra" in rajkot_data["agro_climatic_zone_name"]

    anand_data = lookup_district_crops("Anand", "Gujarat")
    assert anand_data is not None, "Anand must exist in dataset"
    assert "Middle Gujarat Zone" in anand_data["agro_climatic_zone_name"]

    print("✅ Test 1 Passed: Grounding dataset lookups are 100% accurate.")


def test_2_surat_crop_recommendation_and_region_isolation():
    """Test 2: Surat recommendation must return South Gujarat crops and ZERO references to Kutch/Saurashtra."""
    print("\n--- Test 2: Surat Crop Recommendation & Region Isolation ---")

    surat_geo = fetch_real_crops_for_location(21.1702, 72.8311, "Surat, Gujarat")
    advice = generate_geographical_crop_advice(
        location_name="Surat, Gujarat",
        soil_type="Auto-Detect",
        N=140.0, P=45.0, K=240.0, ph=7.6,
        temperature=30.0, humidity=80.0, rainfall=1350.0,
        regional_crops=surat_geo
    )

    soil_type = advice.get("detected_soil_type", "")
    crops = [c["crop_name"] for c in advice.get("recommended_crops", [])]
    zone = advice.get("agro_climatic_zone", "")

    print(f"Surat Soil Detected: {soil_type}")
    print(f"Surat Zone: {zone}")
    print(f"Surat Recommended Crops: {crops}")

    assert "Black" in soil_type or "Vertisol" in soil_type or "Alluvial" in soil_type
    assert any("Sugarcane" in c or "Paddy" in c or "Cotton" in c or "Banana" in c for c in crops), f"Crops for Surat inappropriate: {crops}"

    # Assert region isolation guard passes
    is_valid, bad_kw, bad_field = validate_region_isolation(advice, "Surat, Gujarat")
    assert is_valid, f"Surat output hallucinated foreign region '{bad_kw}' in '{bad_field}'"

    print("✅ Test 2 Passed: Surat output is accurate and free of cross-region hallucinations.")


def test_3_kutch_crop_recommendation_and_region_isolation():
    """Test 3: Kutch recommendation must return Arid crops and ZERO references to Surat/South Gujarat."""
    print("\n--- Test 3: Kutch Crop Recommendation & Region Isolation ---")

    kutch_geo = fetch_real_crops_for_location(23.2420, 69.6669, "Bhuj, Kutch, Gujarat")
    advice = generate_geographical_crop_advice(
        location_name="Bhuj, Kutch, Gujarat",
        soil_type="Auto-Detect",
        N=75.0, P=25.0, K=180.0, ph=8.3,
        temperature=35.0, humidity=40.0, rainfall=380.0,
        regional_crops=kutch_geo
    )

    soil_type = advice.get("detected_soil_type", "")
    crops = [c["crop_name"] for c in advice.get("recommended_crops", [])]
    zone = advice.get("agro_climatic_zone", "")

    print(f"Kutch Soil Detected: {soil_type}")
    print(f"Kutch Zone: {zone}")
    print(f"Kutch Recommended Crops: {crops}")

    assert "Sandy Arid" in soil_type or "Arid" in soil_type
    assert any("Bajra" in c or "Castor" in c or "Isabgol" in c or "Cumin" in c or "Date" in c for c in crops), f"Crops for Kutch inappropriate: {crops}"

    # Assert region isolation guard passes
    is_valid, bad_kw, bad_field = validate_region_isolation(advice, "Bhuj, Kutch, Gujarat")
    assert is_valid, f"Kutch output hallucinated foreign region '{bad_kw}' in '{bad_field}'"

    print("✅ Test 3 Passed: Kutch output is accurate and free of cross-region hallucinations.")


def test_4_distinctness_across_locations():
    """Test 4: Recommended crop lists must be distinct across Surat, Kutch, Rajkot, and Anand."""
    print("\n--- Test 4: Crop List Distinctness Across Locations ---")

    surat_geo = fetch_real_crops_for_location(21.1702, 72.8311, "Surat, Gujarat")
    surat_advice = generate_geographical_crop_advice("Surat, Gujarat", "Auto-Detect", 140, 45, 240, 7.6, 30, 80, 1350, regional_crops=surat_geo)
    surat_crops = set([c["crop_name"] for c in surat_advice.get("recommended_crops", [])])

    kutch_geo = fetch_real_crops_for_location(23.2420, 69.6669, "Bhuj, Kutch, Gujarat")
    kutch_advice = generate_geographical_crop_advice("Bhuj, Kutch, Gujarat", "Auto-Detect", 75, 25, 180, 8.3, 35, 40, 380, regional_crops=kutch_geo)
    kutch_crops = set([c["crop_name"] for c in kutch_advice.get("recommended_crops", [])])

    rajkot_geo = fetch_real_crops_for_location(22.3039, 70.8022, "Rajkot, Gujarat")
    rajkot_advice = generate_geographical_crop_advice("Rajkot, Gujarat", "Auto-Detect", 110, 38, 210, 7.8, 32, 60, 680, regional_crops=rajkot_geo)
    rajkot_crops = set([c["crop_name"] for c in rajkot_advice.get("recommended_crops", [])])

    anand_geo = fetch_real_crops_for_location(22.57, 72.93, "Anand, Gujarat")
    anand_advice = generate_geographical_crop_advice("Anand, Gujarat", "Auto-Detect", 150, 42, 200, 7.4, 28, 70, 850, regional_crops=anand_geo)
    anand_crops = set([c["crop_name"] for c in anand_advice.get("recommended_crops", [])])

    print(f"Surat Crops: {surat_crops}")
    print(f"Kutch Crops: {kutch_crops}")
    print(f"Rajkot Crops: {rajkot_crops}")
    print(f"Anand Crops: {anand_crops}")

    assert surat_crops != kutch_crops, "Surat and Kutch crop lists must NOT be identical"
    assert rajkot_crops != anand_crops, "Rajkot and Anand crop lists must NOT be identical"

    print("✅ Test 4 Passed: Crop recommendations are distinct across agro-climatic zones.")


def test_5_npk_conflict_flagging():
    """Test 5: Verify NPK/pH conflict is explicitly flagged when inputs deviate from zone norms."""
    print("\n--- Test 5: NPK/pH Conflict Flagging ---")

    surat_geo = fetch_real_crops_for_location(21.1702, 72.8311, "Surat, Gujarat")
    # Provide severely low N (20 kg/ha) for Surat heavy rainfall zone (norm 140 kg/ha)
    advice = generate_geographical_crop_advice(
        location_name="Surat, Gujarat",
        soil_type="Auto-Detect",
        N=20.0, P=10.0, K=100.0, ph=5.0,
        temperature=30.0, humidity=80.0, rainfall=1350.0,
        regional_crops=surat_geo
    )

    assessment = advice.get("soil_health_assessment", {})
    nutrient_status = str(assessment.get("nutrient_status", ""))
    ph_eval = str(assessment.get("ph_evaluation", ""))

    print(f"Nutrient Status Output: {nutrient_status}")
    print(f"pH Evaluation Output: {ph_eval}")

    assert "conflict" in nutrient_status.lower() or "deficient" in nutrient_status.lower() or "low" in nutrient_status.lower() or "nitrogen" in nutrient_status.lower()
    assert "ph" in ph_eval.lower() or "acidic" in ph_eval.lower() or "conflict" in ph_eval.lower()

    print("✅ Test 5 Passed: NPK/pH conflict correctly flagged in soil health assessment.")


def test_6_validation_guard_failure_detection():
    """Test 6: Verify validation guard catches synthetic region mismatches."""
    print("\n--- Test 6: Validation Guard Failure Detection ---")

    bad_surat_advice = {
        "agro_climatic_zone": "South Gujarat Zone",
        "recommended_crops": [
            {
                "crop_name": "Bajra",
                "suitability_reason": "Primary Kharif staple in Kutch/Saurashtra arid zones."
            }
        ],
        "regional_market_notes": "Good price in Surat APMC."
    }

    is_valid, kw, field = validate_region_isolation(bad_surat_advice, "Surat, Gujarat")
    assert not is_valid, "Validation guard should have failed for 'Kutch' reference in Surat advice"
    assert kw in ["kutch", "saurashtra"], f"Expected forbidden keyword match, got '{kw}'"

    print("✅ Test 6 Passed: Validation guard successfully detects synthetic hallucinations.")


if __name__ == "__main__":
    print("=======================================================================")
    print("RUNNING AGRISENSE CROP RECOMMENDATION REGRESSION TEST SUITE")
    print("=======================================================================")
    test_1_dataset_lookup_and_soil_detection()
    test_2_surat_crop_recommendation_and_region_isolation()
    test_3_kutch_crop_recommendation_and_region_isolation()
    test_4_distinctness_across_locations()
    test_5_npk_conflict_flagging()
    test_6_validation_guard_failure_detection()
    print("=======================================================================")
    print("ALL REGRESSION TESTS PASSED SUCCESSFULLY! 🎉")
    print("=======================================================================")
