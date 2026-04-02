import streamlit as st
import pymongo
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
import re
from fpdf import FPDF
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = pymongo.MongoClient(MONGO_URI)
db = client["ehr_db"]

# Streamlit UI setup
st.set_page_config(page_title="Patient Condition", layout="wide")
st.title("Proactive Screening Assessment Portal")

# Debug query params
#st.write("Query params:", st.query_params)
raw_query = st.query_params.get("patient_id")

if not raw_query:
    st.error("There was no patient_id provided in URL.")
    st.stop()

patient_id = raw_query[0] if isinstance(raw_query, list) else raw_query

# Query patient
patient = db["Patient"].find_one({"id": patient_id})
if not patient:
    st.error(f"No patient found with the following ID {patient_id}")
    st.stop()

# Display patient name
name_info = patient.get("name", [{}])[0]
full_name = f"{name_info.get('given', [''])[0]} {name_info.get('family', '')}".strip()

st.subheader(f"👤 Patient: {full_name}")
st.write(f"**Gender:** {patient.get('gender', 'Unknown')}  ")
st.write(f"**Birth Date:** {patient.get('birthDate', 'Unknown')}  ")
st.write(f"**Age:** {patient.get('calculated_age', 'N/A')}  ")
# Enforce age-based access
age = patient.get("calculated_age")
if isinstance(age, int) and age < 45:
    st.warning("⚠️ This portal is intended only for patients 45 years and older. Access is restricted.")
    st.stop()

# Tabs
tab_main, tab_charts, tab_notes = st.tabs(["Main", "Charts", "Clinician Notes"])

with tab_main:
    st.markdown("### Active Clinical Conditions with ICD-10 Mapping")

    # Fetch only ACTIVE conditions for the patient
    conditions = list(db["Condition"].find({
        "subject.reference": f"Patient/{patient_id}",
        "clinicalStatus.coding.code": "active"
    }))

    UMLS_API_KEY = os.getenv("UMLS_API_KEY")

    def get_icd10_mapping(snomed_code, api_key):
        try:
            # Step 1: Search for CUI
            search_url = "https://uts-ws.nlm.nih.gov/rest/search/current"
            search_params = {
                "string": snomed_code,
                "apiKey": api_key
            }
            search_response = requests.get(search_url, params=search_params, timeout=10)
            search_data = search_response.json()

            results = search_data.get('result', {}).get('results', [])
            if not results:
                return [{"code": "N/A", "name": "No CUI found"}]

            cui = results[0].get('ui')
            if not cui or cui.startswith("NONE"):
                return [{"code": "N/A", "name": "Invalid or missing CUI"}]

            # Step 2: Map CUI to ICD-10
            mapping_url = f"https://uts-ws.nlm.nih.gov/rest/content/current/CUI/{cui}/atoms"
            mapping_params = {"apiKey": api_key}
            mapping_response = requests.get(mapping_url, params=mapping_params, timeout=10)
            mapping_data = mapping_response.json()

            icd10_codes = []
            for atom in mapping_data.get('result', []):
                if atom.get('rootSource') == 'ICD10CM':
                    icd10_codes.append({
                        'code': atom.get('code'),
                        'name': atom.get('name')
                    })

            return icd10_codes if icd10_codes else [{"code": "N/A", "name": "No ICD-10 mappings found"}]

        except Exception as e:
            return [{"code": "N/A", "name": f"Error: {str(e)}"}]

    # Process and display only valid conditions
    clinical_terms = [
        "disease", "disorder", "syndrome", "cancer", "infection", "failure",
        "injury", "deficiency", "diabetes", "asthma", "arthritis", "attack"
    ]
    filtered_conditions = []
    for c in conditions:
        coding = c.get("code", {}).get("coding", [{}])[0]
        display = coding.get("display", "").lower()
        system = coding.get("system", "")

        if "snomed" in system.lower() and any(term in display for term in clinical_terms):
            snomed_code = coding.get("code", "")
            icd10_list = get_icd10_mapping(snomed_code, UMLS_API_KEY)
            icd10_str = ", ".join([f"{item['code']} ({item['name']})" for item in icd10_list]) if icd10_list else "N/A"

            filtered_conditions.append({
                "SNOMED Code": snomed_code,
                "Condition": coding.get("display", "N/A"),
                "ICD-10 Mapping": icd10_str,
                "Status": c.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "N/A"),
                "Onset": c.get("onsetDateTime", "N/A"),
                "Abatement": c.get("abatementDateTime") or "N/A"
            })

    # Filter the data to show only active conditions
    if filtered_conditions:
        cond_df = pd.DataFrame(filtered_conditions)
        st.dataframe(cond_df)
    else:
        st.info("No active clinical conditions with SNOMED found for this patient.")


with tab_charts:
    st.markdown("Data Visualizations")

    # 1. Histogram of ages across all patients
    st.subheader("Age Distribution of All Patients")

    all_patients = list(db["Patient"].find())
    ages = [
        p.get("calculated_age")
        for p in all_patients
        if isinstance(p.get("calculated_age"), int)
    ]
    current_age = patient.get("calculated_age")

    if ages:
        fig1, ax1 = plt.subplots()
        ax1.hist(ages, bins=10, edgecolor="black", alpha=0.7)
        ax1.axvline(x=45, color="red", linestyle="--", label="Screening Threshold (45)")
        
        if isinstance(current_age, int):
            ax1.axvline(x=current_age, color="blue", linestyle="dashdot", label=f"Current Patient Age ({current_age})")

        ax1.set_xlabel("Age")
        ax1.set_ylabel("Count")
        ax1.set_title("Patient Age Distribution")
        ax1.legend()
        st.pyplot(fig1)
    else:
        st.warning("No valid ages found in patient records.")

    # 2. Condition Timeline
    st.subheader("Condition Timeline (Current Patient)")

    # Extract timeline data from filtered_conditions
    timeline_records = []
    for cond in filtered_conditions:
        onset = cond.get("Onset")
        label = cond.get("Condition", "N/A")
        if onset and onset != "N/A":
            timeline_records.append({
                "Condition": label,
                "Onset": onset
            })

    timeline_df = pd.DataFrame(timeline_records)

    if not timeline_df.empty:
        timeline_df["Onset"] = pd.to_datetime(timeline_df["Onset"], errors="coerce")
        timeline_df = timeline_df.dropna(subset=["Onset"]).sort_values("Onset")

        # Plot as horizontal bar chart of rank
        fig, ax = plt.subplots(figsize=(8, max(4, len(timeline_df) * 0.4)))
        ax.barh(timeline_df["Condition"], timeline_df["Onset"].rank())
        ax.set_yticks(range(len(timeline_df)))
        ax.set_yticklabels(timeline_df["Condition"])
        ax.set_xlabel("Relative Onset Order")
        ax.set_title("Timeline of Diagnosed Conditions")
        st.pyplot(fig)
    else:
        st.info("No valid onset-dated conditions found for this patient.")
    
    display_names = [c["Condition"] for c in filtered_conditions if c.get("Condition")]
    condition_display_counts = pd.Series(display_names).value_counts().head(10)


    if not condition_display_counts.empty:
        fig3, ax3 = plt.subplots()
        condition_display_counts.plot(kind="barh", ax=ax3)
        ax3.set_xlabel("Count")
        ax3.set_ylabel("Condition")
        ax3.set_title("Top Diagnosed Conditions")
        st.pyplot(fig3)
    else:
        st.info("No conditions found to chart.")


import requests

with tab_notes:
    st.markdown("Clinician Notes")

    # Retrieve existing notes
    notes = list(db["clinician_notes"].find({"patient_id": patient_id}).sort("timestamp", -1))

    if notes:
        for n in notes:
            st.markdown(f"*{n.get('timestamp', 'Unknown')}*")
            st.write(n.get("note", ""))
            st.markdown("---")

        # Generate PDF in memory
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"Clinician Notes for {full_name}", ln=True, align="C")
        pdf.ln(10)  # Add spacing after the title
        pdf.set_font("Arial", size=12)


        for n in notes:
            timestamp = n.get("timestamp", "")
            note = n.get("note", "")
            pdf.multi_cell(0, 10, f"{timestamp}\n{note}\n")

        pdf_output = pdf.output(dest="S").encode("latin-1")  # FPDF requires latin-1 encoding

        st.download_button(
            label="Download Notes as PDF",
            data=pdf_output,
            file_name=f"{full_name.replace(' ', '_')}_clinician_notes.pdf",
            mime="application/pdf"
        )

    else:
        st.info("No existing notes found.")

    st.markdown("Add New Note")

    # Use a form to handle submission cleanly
    with st.form("add_note_form", clear_on_submit=True):
        new_note = st.text_area("Write your note here...", height=150)
        submitted = st.form_submit_button("Save Note")

        if submitted:
            if new_note.strip():
                db["clinician_notes"].insert_one({
                    "patient_id": patient_id,
                    "note": new_note.strip(),
                    "timestamp": pd.Timestamp.now().isoformat()
                })
                st.success("Note saved successfully!")
                st.rerun()  # refresh to show the new note
            else:
                st.warning("Note cannot be empty.")