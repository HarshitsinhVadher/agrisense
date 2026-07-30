import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from services.label_service import _clean_and_parse_json, _normalize_ai_fields

print("=== TESTING LABEL SCANNER RESPONSE PARSER & FIELD NORMALIZER ===")

# Test 1: Markdown code block stripping with extra commentary
raw_response_1 = """Here is the structured JSON output for the label:
```json
{
    "productName": "Chlorpyrifos 20% EC",
    "brand": "Tata Rallis",
    "activeIngredient": "Chlorpyrifos 20%",
    "formulationType": "EC",
    "dosagePerAcre": "500 ml/acre",
    "dosagePerLiterWater": "2 ml/L water",
    "targetPests": ["Stem Borer", "Leaf Folder"],
    "confidenceScore": 95
}
```
Hope this helps!"""

parsed_1 = _clean_and_parse_json(raw_response_1)
assert parsed_1 is not None, "Failed to parse markdown fence"
norm_1 = _normalize_ai_fields(parsed_1)

print("\n--- Test 1 Results ---")
print("Product Name:", norm_1["product_name"])
print("Manufacturer:", norm_1["manufacturer"])
print("Active Ingredient:", norm_1["active_ingredient"])
print("Dosage Acre:", norm_1["dosage_per_acre"])
print("Dosage Liter:", norm_1["dosage_per_liter_water"])
print("Target Pests:", norm_1["target_pests_or_crops"])

assert norm_1["product_name"] == "Chlorpyrifos 20% EC"
assert norm_1["manufacturer"] == "Tata Rallis"
assert norm_1["active_ingredient"] == "Chlorpyrifos 20%"
assert norm_1["dosage_per_acre"] == "500 ml/acre"

# Test 2: Field variations (active, company, rate)
raw_response_2 = """{
    "name": "Neem Shield Bio Pesticide",
    "company": "Neem India Ltd",
    "active": "Azadirachtin 10000 PPM",
    "type_code": "EC",
    "rate": "3 ml per liter water",
    "crops": "Cotton, Paddy, Groundnut",
    "score": 90
}"""

parsed_2 = _clean_and_parse_json(raw_response_2)
norm_2 = _normalize_ai_fields(parsed_2)

print("\n--- Test 2 Results ---")
print("Product Name:", norm_2["product_name"])
print("Manufacturer:", norm_2["manufacturer"])
print("Active Ingredient:", norm_2["active_ingredient"])
print("Dosage Rate:", norm_2["dosage"])
print("Target Crops:", norm_2["target_pests_or_crops"])

assert norm_2["product_name"] == "Neem Shield Bio Pesticide"
assert norm_2["manufacturer"] == "Neem India Ltd"
assert norm_2["active_ingredient"] == "Azadirachtin 10000 PPM"
assert norm_2["dosage"] == "3 ml per liter water"

print("\n✅ ALL RESPONSE PARSER TESTS PASSED SUCCESSFULLY!")
