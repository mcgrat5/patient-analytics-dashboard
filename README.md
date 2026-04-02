# Patient Analytics Dashboard (Healthcare Data)

Interactive dashboard for exploring patient clinical data, including conditions, screening history, and clinician notes

## Overview
This project is a healthcare dashboard that allows users to search for patients and explore their clinical information in an interactive interface. The application connects to a MongoDB database containing FHIR-based patient data and provides tools for analyzing patient demographics, conditions, and screening recommendations

Unlike the full clinical decision support system, this application is centered on **data exploration, visualization, and user interaction**, rather than backend decision logic

This project represents the dashboard and data exploration component of a larger clinical decision support system

## Features
- Interactive dashboard for exploring clinical data
- Age-based indicators for screening eligibility
- Visualization of patient conditions and screening assessnents
- Clinician note creation and tracking

## Tech Stack
- Python (Streamlit)
- MongoDB
- FHIR (NDJSON data format)
- Pandas

## How It Works
1) User enters a patient ID
2) Application retrieves patient data from MongoDB
3) Dashboard displays:
    - Patient demographics
    - Clinical conditions
    - Screening data
    - Clinician notes
4) Users can interact with and add or update patient notes

## Interface
This application provides an interactive interface for exploring patient clinical data, including demographics, conditions, screening assignments, and clinician notes

## Setup Instructions
1) Clone the repository
2) Install dependencies (Poetry):
    poetry install
3) Ensure MongoDB is running locally
4) Load FHIR NDJSON data into MongoDB
5) Run the application:
    streamlit run app.py

## Notes
- Full FHIR NDJSON datasets are not included due to file size
- The application was developed using de-identified and synthetic patient data
- Requires a local MongoDB instance

## Future Improvements
- Add advanced filtering and cohort selection tools
- Enhance visualizations for patient trends
- Improve UI design
- Deploy as a hosted web application

## Author
Connor McGrath