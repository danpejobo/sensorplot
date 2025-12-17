import streamlit as st
from sensorplot.app import run_app

# 1. Konfigurer siden
# Dette setter fanetittel og layout kun for denne undersiden.
st.set_page_config(
    page_title="Sensor Analyse", 
    page_icon="📈", 
    layout="wide"
)

# 2. (Valgfritt) Legg til ekstra info fra hoved-appen din
st.markdown("# Integrert Analyseverktøy")
st.caption("Dette verktøyet lar deg korrigere og plotte loggerdata.")

# 3. Kjør Sensorplot
# Dette tegner hele GUI-et (Sidebar + Plot) inne i denne siden.
run_app()