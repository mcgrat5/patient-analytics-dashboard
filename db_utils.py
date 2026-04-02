from pymongo import MongoClient

# Flexible import for flat_file_utils
try:
    from . import flat_file_utils as ffu
except ImportError:
    import flat_file_utils as ffu


def connect():
    """Establish a connection to MongoDB and return client and db handle."""
    client = MongoClient('mongodb://localhost:27017/')
    db = client['ehr_db']
    return client, db


def populate():
    """Load and insert all FHIR resource types using flat_file_utils."""
    ffu.load_all_reference_types()


def drop_collections():
    """Drop all FHIR collections defined in flat_file_utils.ref_types."""
    client, db = connect()
    for r in ffu.ref_types:
        print(f"Dropping collection: {r}")
        db.drop_collection(r)
    client.close()


def insert_age_screening_result(screening_data):
    """Insert an age-based screening assessment into the 'age_screening_assessments' collection."""
    client, db = connect()
    db["age_screening_assessments"].insert_one(screening_data)
    client.close()


if __name__ == "__main__":
    populate()
