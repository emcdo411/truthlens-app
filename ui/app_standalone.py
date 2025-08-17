import sys
import os
import re
from datetime import datetime
import streamlit as st

# Set the project root to the truthlens folder
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Debug paths to diagnose import issues
print(f"Project root: {ROOT}")
print(f"Python search paths: {sys.path}")
print(f"Does 'app' folder exist? {os.path.exists(os.path.join(ROOT, 'app'))}")
print(f"Does 'app/services' folder exist? {os.path.exists(os.path.join(ROOT, 'app', 'services'))}")
print(f"Files in 'app/services': {os.listdir(os.path.join(ROOT, 'app', 'services')) if os.path.exists(os.path.join(ROOT, 'app', 'services')) else 'Not found'}")
print(f"Does 'app/config.py' exist? {os.path.exists(os.path.join(ROOT, 'app', 'config.py'))}")

# Try to load the services
try:
    from app.services import (
        summarize,
        extract_claims,
        search_web,
        assess_claim,
        trust_weight,
        aggregate_truth_score,
        star_rating_from_quality,
        fetch_transcript_youtube,
    )
except ImportError as e:
    st.error(
        f"Error loading services: {e}. "
        "Check that the 'app' folder is in your truthlens folder, "
        "and the 'services' folder has these files: llm.py, summarizer.py, claim_extractor.py, "
        "searcher.py, fact_checker.py, scoring.py, transcript.py, plus __init__.py. "
        "Also ensure 'app/config.py' exists."
    )
    st.stop()

# Show which 'app' package is loaded
try:
    import importlib
    st.caption(f"Using app package at: {importlib.import_module('app').__file__}")
except Exception:
    pass

# Page config
st.set_page_config(page_title="TruthLens — Standalone", layout="wide")
st.title("TruthLens — Standalone (no backend)")

# Copy Streamlit secrets to environment variables
def sync_env_from_secrets(required: list[str], optional: list[str]) -> None:
    try:
        secrets = st.secrets
    except Exception:
        secrets = {}
        st.warning("No secrets.toml found. Ensure API keys are set in environment variables.")
    for k in required + optional:
        if k in secrets and not os.environ.get(k):
            os.environ[k] = str(secrets[k])
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        st.error(f"Missing required keys: {', '.join(missing)}")
        st.stop()

# Only OpenAI is strictly required; Tavily and YouTube are optional
sync_env_from_secrets(required=["OPENAI_API_KEY"], optional=["TAVILY_API_KEY", "YT_API_KEY"])

with st.sidebar:
    st.subheader("Runtime Status")
    st.markdown(
        "OpenAI key: **{}**<br>"
        "YouTube key: **{}**<br>"
        "Tavily key: **{}**".format(
            "✅" if os.environ.get("OPENAI_API_KEY") else "❌",
            "✅" if os.environ.get("YT_API_KEY") else "⚪️ optional",
            "✅" if os.environ.get("TAVILY_API_KEY") else "⚪️ optional",
        ),
        unsafe_allow_html=True,
    )
    st.markdown("This app calls your service modules directly — **no FastAPI server required**.")

# Helpers
def parse_sections(raw: str) -> tuple[list[str], str, str]:
    def extract(name: str) -> str:
        m = re.search(rf"{name}\s*:?\s*\n(.+?)(?:\n\n|$)", raw, flags=re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else ""
    tldr = [x.strip("- ").strip() for x in extract("TL;DR").split("\n") if x.strip()]
    summary = extract("Executive Summary") or "(no executive summary extracted)"
    deep = extract("Deep Dive") or "(no deep dive extracted)"
    return (tldr or ["(no TL;DR extracted)"], summary, deep)

def run_pipeline(text: str, source_type: str = "Text", source_url: str = "") -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f"TruthLens Report ({source_type})" + (f" — {source_url}" if source_url else "")

    # 1) Summarize
    try:
        sum_raw = summarize(text)["raw"]
    except Exception as e:
        st.error(f"Summarizer failed: {e}. Ensure OPENAI_API_KEY is valid.")
        st.stop()

    # 2) Extract claims
    claims_raw = []
    try:
        claims_raw = extract_claims(text, k=8) or []
    except Exception as e:
        st.warning(f"Claim extraction failed: {e}. Continuing without claims.")

    # 3) Search and assess claims
    claim_assessments = []
    global_sources = []
    has_search = bool(os.environ.get("TAVILY_API_KEY"))

    for claim in claims_raw:
        claim_text = claim.get("text", "")
        queries = claim.get("proposed_queries", [claim_text])[:3]
        search_results = []

        if has_search:
            for query in queries:
                try:
                    search_results += search_web(query, max_results=3)
                except Exception as e:
                    st.warning(f"Search failed for query '{query}': {e}. Skipping.")

        source_entries = []
        snippets = []
        for result in search_results[:5]:
            url = result.get("url")
            if not url:
                continue
            trust_score = trust_weight(url)
            source_entry = {
                "url": url,
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "trust_weight": trust_score
            }
            source_entries.append(source_entry)
            snippets.append(f"{source_entry['title']} — {source_entry['snippet']}")
            global_sources.append(source_entry)

        try:
            assessment = assess_claim(claim_text, snippets)
            support_score = float(assessment.get("support_score", 0.0))
            contradiction_score = float(assessment.get("contradiction_score", 0.0))
            rationale = assessment.get("rationale", "No rationale provided.")
        except Exception as e:
            support_score, contradiction_score = 0.0, 0.0
            rationale = f"Assessment failed: {e}"

        claim_assessments.append({
            "claim": {"text": claim_text, "snippet": claim.get("snippet", ""), "proposed_queries": queries},
            "support_score": support_score,
            "contradiction_score": contradiction_score,
            "sources": source_entries,
            "rationale": rationale
        })

    truth_score = aggregate_truth_score(claim_assessments)
    stars = star_rating_from_quality(clarity=0.8, evidence=min(1.0, truth_score/100.0), bias=0.3)

    tldr, summary, deep = parse_sections(sum_raw)

    md = f"""# {title}
**Generated:** {ts}  
**Truth Score:** {truth_score:.1f}/100  
**Stars (Critical Style):** {stars:.1f}/5

## TL;DR
- {"\n- ".join(tldr)}

## Executive Summary
{summary}

## Deep Dive
{deep}

## Claims & Evidence
"""
    if claim_assessments:
        md += "\n".join(
            f"- **Claim:** {a['claim']['text']}\n"
            f"  - Support: {a['support_score']:.2f}, Contra: {a['contradiction_score']:.2f}\n"
            f"  - Rationale: {a['rationale']}\n"
            f"  - Sources: " + (
                ", ".join([f"[{s.get('title') or s.get('url')}]({s.get('url')})" for s in a['sources']])
                if a["sources"] else "(none)"
            )
            for a in claim_assessments
        )
    else:
        md += "_No claims extracted or evidence search unavailable._"

    return md

# UI
tab1, tab2 = st.tabs(["YouTube", "Text/Web"])

with tab1:
    url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
    if st.button("Analyze YouTube"):
        if not url.strip():
            st.warning("Please paste a YouTube URL.")
        elif not re.match(r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]{11}", url):
            st.warning("Please enter a valid YouTube URL.")
        else:
            with st.spinner("Fetching transcript…"):
                try:
                    text, _timed = fetch_transcript_youtube(url)
                except Exception as e:
                    text = None
                    st.error(f"Transcript fetch failed: {e}")
            if not text:
                st.error("No public transcript found. Try another video or use the Text/Web tab.")
            else:
                with st.spinner("Analyzing…"):
                    md = run_pipeline(text, source_type="YouTube", source_url=url)
                st.success("Done.")
                st.markdown(md)
                st.download_button("Download report (.md)", md, file_name="truthlens_youtube.md")

with tab2:
    content = st.text_area("Paste text you have rights to use", height=220)
    if st.button("Analyze Text"):
        if not content.strip():
            st.warning("Please paste some text.")
        else:
            with st.spinner("Analyzing…"):
                md = run_pipeline(content, source_type="Text")
            st.success("Done.")
            st.markdown(md)
            st.download_button("Download report (.md)", md, file_name="truthlens_text_report.md")

