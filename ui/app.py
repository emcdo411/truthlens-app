# ui/app.py
import os
import json
import requests
import streamlit as st

st.set_page_config(page_title="TruthLens", layout="wide")
st.title("TruthLens (API-backed UI)")

# Where is the FastAPI backend?
BACKEND = (
    os.environ.get("TRUTHLENS_BACKEND")
    or getattr(st.secrets, "get", lambda *_: None)("TRUTHLENS_BACKEND")  # works on Streamlit Cloud
    or "http://127.0.0.1:8000"
)

with st.sidebar:
    st.subheader("Backend")
    st.code(BACKEND, language="text")

def health_badge():
    try:
        r = requests.get(f"{BACKEND}/health", timeout=3)
        if r.status_code == 200:
            try:
                data = r.json()
                if data.get("status") == "ok":
                    st.success("🟢 API health: OK")
                else:
                    st.warning(f"🟡 API health: {data}")
            except Exception:
                st.warning(f"🟠 API returned non-JSON despite 200: {r.text[:200]}")
        else:
            st.error(f"🔴 API error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        st.error(f"🔴 API unreachable: {e}")

health_badge()
st.divider()

def api_post(path: str, payload: dict, timeout: int = 180):
    url = f"{BACKEND}{path}"
    try:
        r = requests.post(url, json=payload, timeout=timeout)
    except requests.exceptions.RequestException as e:
        st.error(f"Network error calling {url}: {e}")
        st.stop()

    if r.status_code != 200:
        st.error(f"API error {r.status_code} for {path}")
        st.code((r.text or "<empty response>")[:2000])
        st.stop()

    # Only parse JSON when the response looks like JSON
    ct = (r.headers.get("content-type") or "").lower()
    if "application/json" not in ct:
        # try a best-effort parse, else show raw text
        try:
            return json.loads(r.text)
        except Exception:
            st.error("API returned non-JSON. Raw response:")
            st.code((r.text or "<empty>")[:2000])
            st.stop()

    try:
        return r.json()
    except ValueError:
        st.error("Failed to decode JSON from API. Raw response:")
        st.code((r.text or "<empty>")[:2000])
        st.stop()

tab1, tab2 = st.tabs(["YouTube", "Text/Web"])

with tab1:
    url = st.text_input("YouTube URL")
    if st.button("Analyze Video"):
        if not url.strip():
            st.warning("Please paste a YouTube URL.")
        else:
            with st.spinner("Analyzing via backend..."):
                data = api_post("/analyze/youtube", {"url": url})
            st.success("Done.")
            st.markdown(data.get("markdown_report", "No report generated."))

with tab2:
    content = st.text_area("Paste text you have rights to use", height=220)
    if st.button("Analyze Text"):
        if not content.strip():
            st.warning("Please paste some text.")
        else:
            with st.spinner("Analyzing via backend..."):
                data = api_post("/analyze/text", {"content": content})
            st.success("Done.")
            st.markdown(data.get("markdown_report", "No report generated."))

