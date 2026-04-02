import streamlit as st
import pandas as pd
import requests
import uuid
from db_utils import connect
from datetime import datetime
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()
UMLS_API_KEY = os.getenv("UMLS_API_KEY")

st.set_page_config(page_title="Proactive Health Screening Portal", layout="wide")
st.title("Proactive Screening Assessment Portal")

# Session state initialziation
if "stage" not in st.session_state:
    st.session_state.stage = "lookup"
if "patient_id" not in st.session_state:
    st.session_state.patient_id = None

# Lookup stage
if st.session_state.stage == "lookup":
    st.subheader("Enter Patient ID")
    pid = st.text_input("Patient ID")

    if st.button("Submit"):
        client, db = connect()
        patient = db["Patient"].find_one({"id": pid})
        client.close()

        if patient:
            st.session_state.patient_id = pid
            st.session_state.stage = "summary"

            # Immediate preview
            name_data = patient.get("name", [{}])[0]
            full_name = f"{name_data.get('given', [''])[0]} {name_data.get('family', '')}".strip()
            birth_date = patient.get("birthDate", "Unknown")
            gender = patient.get("gender", "Unknown").capitalize()
            try:
                age = datetime.now().year - datetime.strptime(birth_date, "%Y-%m-%d").year
            except:
                age = "Unknown"

            st.markdown("Patient Card")
            st.markdown(f"- **👤 Name:** {full_name}")
            st.markdown(f"- **🚻 Gender:** {gender}")
            st.markdown(f"- **🎂 Age:** {age}")
            st.markdown(f"- **📅 Birth Date:** {birth_date}")
            if isinstance(age, int) and age >= 45:
                st.success("✅ This patient is eligible for age-based proactive screenings.")
            elif isinstance(age, int):
                st.info("ℹ️ This patient is under 45 and may not require proactive screenings.")
            else:
                st.warning("⚠️ Unable to determine screening eligibility.")

            url = f"http://localhost:8502/?patient_id={pid}"
            st.markdown(
                f'<a href="{url}" target="_blank"><button>🚀 Open Proactive Screening Dashboard</button></a>',
                unsafe_allow_html=True
            )
        else:
            st.error("Patient not found. Please try again.")

# Summary stage
elif st.session_state.stage == "summary":
    patient_id = st.session_state.patient_id
    client, db = connect()
    patient = db["Patient"].find_one({"id": patient_id})
    assessments = list(db["age_screening_assessments"].find({"patient_id": patient_id}))
    notes = list(db["clinical_notes"].find({"patient_id": patient_id}))
    conditions = list(db["Condition"].find({"subject.reference": f"Patient/{patient_id}"}))
    client.close()

    name_data = patient.get("name", [{}])[0]
    full_name = f"{name_data.get('given', [''])[0]} {name_data.get('family', '')}".strip()
    birth_date = patient.get("birthDate", "Unknown")
    gender = patient.get("gender", "Unknown").capitalize()
    try:
        age = datetime.now().year - datetime.strptime(birth_date, "%Y-%m-%d").year
    except:
        age = "Unknown"

    st.subheader(f"👤 Patient Profile: {patient_id}")
    st.markdown(f"- **👤 Name:** {full_name}")
    st.markdown(f"- **🚻 Gender:** {gender}")
    st.markdown(f"- **🎂 Age:** {age}")
    st.markdown(f"- **📅 Birth Date:** {birth_date}")
    if isinstance(age, int) and age >= 45:
        st.success("✅ This patient is eligible for age-based proactive screenings.")
    elif isinstance(age, int):
        st.info("ℹ️ This patient is under 45 and may not require proactive screenings.")
    else:
        st.warning("⚠️ Unable to determine screening eligibility.")

    # SNOMED Codes
    snomed_terms = []
    for c in conditions:
        code_data = c.get("code", {}).get("coding", [{}])[0]
        if "snomed" in code_data.get("system", "").lower():
            code = code_data.get("code")
            display = code_data.get("display", "Unknown")
            if code:
                snomed_terms.append(f"{code} – {display}")
    if snomed_terms:
        st.markdown("Ontology Mappings (SNOMED):")
        for term in snomed_terms:
            st.markdown(f"- {term}")
    else:
        st.markdown("Ontology Mappings:")
        st.info("No SNOMED codes found for this patient.")

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Notes", "📋 Demographics", "🧪 Risk Screening", "🚨 CDS Hook"])

    with tab1:
        st.markdown("Add Clinical Notes")
        for note in sorted(notes, key=lambda x: x["timestamp"], reverse=True):
            st.markdown(f"- {note['timestamp'].strftime('%Y-%m-%d %H:%M')} — {note['note']}")
        note = st.text_area("Write new note")
        if st.button("Save Note"):
            client, db = connect()
            db["clinical_notes"].insert_one({
                "patient_id": patient_id,
                "note": note,
                "timestamp": datetime.now()
            })
            client.close()
            st.success("✅ Note saved.")

    with tab2:
        st.markdown("Demographic Info")
        st.markdown(f"**Name:** {full_name}")
        st.markdown(f"**Gender:** {gender}")
        st.markdown(f"**Birth Date:** {birth_date}")
        st.markdown(f"**Age:** {age}")

    with tab3:
        st.markdown("Age-Based Risk Screenings")
        if assessments:
            df = pd.DataFrame(assessments)
            df["assessment_date"] = df["assessment_date"].apply(
                lambda d: d.strftime("%Y-%m-%d") if isinstance(d, datetime) else d
            )
            st.dataframe(df[["assessment_date", "age_at_assessment", "screening_needed",
                             "recommended_medication", "associated_condition"]])
        else:
            st.info("No screening assessments found for this patient.")

    with tab4:
        st.markdown("Trigger CDS Hook")
        if st.button("Run CDS Hook"):
            hook_payload = {
                "hook": "patient-view",
                "context": {"patientId": patient_id},
                "hookInstance": str(uuid.uuid4())
            }
            try:
                response = requests.post("http://localhost:5005/cds-services/age-risk-check", json=hook_payload)
                if response.status_code == 200:
                    cards = response.json().get("cards", [])
                    if cards:
                        for card in cards:
                            st.markdown(f"**{card.get('summary', 'CDS Alert')}**")
                            st.write(card.get("detail", ""))
                            for link in card.get("links", []):
                                st.markdown(
                                    f'<a href="{link["url"]}" target="_blank"><button>🚀 Open Proactive Screening Portal</button></a>',
                                    unsafe_allow_html=True
                                )
                    else:
                        st.success("✅ No alerts from CDS service.")
                else:
                    st.error("CDS service error.")
            except Exception as e:
                st.error(f"CDS hook failed: {e}")

    if st.button("Back to Lookup"):
        st.session_state.stage = "lookup"
        st.session_state.patient_id = None