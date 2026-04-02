import json
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["ehr_db"]

# List of FHIR resource types to ingest
ref_types = [
    "Patient", "Condition", "Observation", "Procedure",
    "AllergyIntolerance", "Device", "DiagnosticReport", "DocumentReference",
    "Encounter", "Immunization", "MedicationRequest"
]

DATA_FOLDER = Path(".")

def calculate_age(birth_date_str):
    try:
        birth = datetime.strptime(birth_date_str, "%Y-%m-%d")
        today = datetime.today()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    except Exception:
        return None

def load_reference_type(ref_type):
    files = sorted(DATA_FOLDER.glob(f"{ref_type}.*.ndjson"))
    collection = db[ref_type]
    collection.delete_many({})  # Optional: clear existing data

    for file_path in files:
        print(f"Loading {file_path.name}...")
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                try:
                    entry = json.loads(line)
                    resource = entry.get("resource", entry)  # flatten if wrapped

                    # Debug: Print first Patient record to inspect its structure
                    if ref_type == "Patient" and i == 0:
                        print("🔍 First Patient record:")
                        print(json.dumps(resource, indent=2))

                    # Enrich Patient with calculated age
                    if ref_type == "Patient" and "birthDate" in resource:
                        resource["calculated_age"] = calculate_age(resource["birthDate"])

                    collection.insert_one(resource)
                except Exception as e:
                    print(f"❌ Error in {file_path.name} line {i+1}: {e}")

    print(f"✅ {ref_type} loaded into MongoDB.")

def load_all_reference_types():
    for ref in ref_types:
        load_reference_type(ref)

if __name__ == "__main__":
    load_all_reference_types()
