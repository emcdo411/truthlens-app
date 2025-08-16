import streamlit as st
import requests, os

st.set_page_config(page_title="TruthLens", layout="wide")
st.title("TruthLens")

backend = os.environ.get("TRUTHLENS_BACKEND", "http://localhost:8000")

tab1, tab2 = st.tabs(["YouTube", "Text/Web"])

with tab1:
    url = st.text_input("YouTube URL")
    if st.button("Analyze Video") and url:
        r = requests.post(f"{backend}/analyze/youtube", json={"url": url})
        st.write(r.json())

with tab2:
    content = st.text_area("Paste text (e.g., book foreword you have rights to use)")
    if st.button("Analyze Text") and content.strip():
        r = requests.post(f"{backend}/analyze/text", json={"content": content})
        data = r.json()
        st.markdown(data.get("markdown_report",""))
