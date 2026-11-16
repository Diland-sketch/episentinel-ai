"""Compatible standalone entry for the historical laboratory."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st
from app.historical_app import VIEWS, render

def main():
    st.set_page_config(page_title="EpiSentinel AI · Laboratorio histórico", page_icon="◈", layout="wide")
    st.markdown((ROOT / "app/analysis_styles.css").read_text(encoding="utf-8"), unsafe_allow_html=True)
    st.title("Laboratorio de Machine Learning")
    view = st.radio("Recorrido histórico", VIEWS, horizontal=True, key="epi_lab_view")
    render(view)

if __name__ == "__main__":
    main()
