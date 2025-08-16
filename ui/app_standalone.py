import sys
import os
import re
import streamlit as st
from datetime import datetime

# Set up project root path safely
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Avoid modifying sys.modules unless absolutely necessary
# Ensure local 'app' module is used by prioritizing ROOT in sys.path

# Import services from local package
try:
    from app.services import (
        summarizer,
        claim_extractor,
        searcher,
        fact_checker,
        scoring,
        transcript,
    )
except ImportError as e:
    st.error(f"Failed to import services: {e}. Ensure 'app.services' is correctly set up.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Streamlit page config
st.set_page_config(page_title="TruthLens — Standalone", layout="wide")
st.title("TruthLens — Standalone (no backend)")

# Sync Streamlit secrets to environment variables
def _sync_env_from_secrets(keys):
    try:
        secrets = st.secrets
    except Exception:
        secrets = {}
        st.warning("No secrets.toml found. Ensure API keys are set in environment variables.")
    for key in keys:
        if key in secrets and not os.environ.get(key):
            os.environ[key] = str(secrets[key])
        if not os.environ.get(key):
            if key == "TAVILY_API_KEY":
                st.warning(f"{key} not set. Search functionality will be skipped.")
            else:
                st.error(f"{key} is required but not set.")
                st.stop()

# Sync required API keys
_sync_env_from_secrets(["OPENAI_API_KEY", "TAVILY_API_KEY", "YT_API_KEY"])

# Sidebar: Display API key status
with st.sidebar:
    st.subheader("Runtime Status")
    st.caption(
        f"OpenAI key: {'✅' if os.environ.get('OPENAI_API_KEY') else '❌'}<br>"
        f"YouTube key: {'✅' if os.environ.get('YT_API_KEY') else '❌'}<br>"
        f"Tavily key: {'✅' if os.environ.get('TAVILY_API_KEY') else '⚪️ optional'}",
        unsafe_allow_html=True
    )
    st.markdown(
        "This app calls your service modules directly — "
        "**no FastAPI server required**."
    )

# ─────────────────────────────────────────────────────────────────────────────
# Helpers

def _parse_sections(raw: str) -> tuple[list[str], str, str]:
    """Parse TL;DR, Executive Summary, and Deep Dive sections from raw text."""
    def extract_section(name: str) -> str:
        pattern = rf"{name}\s*:?\s*\n(.+?)(?:\n\n|$)"
        match = re.search(pattern, raw, flags=re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""
    
    tldr = [x.strip("- ").strip() for x in extract_section("TL;DR").split("\n") if x.strip()]
    summary = extract_section("Executive Summary")
    deep = extract_section("Deep Dive")
    return tldr or ["(no TL;DR extracted)"], summary or "(no executive summary extracted)", deep or "(no deep dive extracted)"

def _run_pipeline(text: str, source_type: str = "text", source_url: str = "") -> str:
    """Run the TruthLens pipeline: summarize, extract claims, search, and assess."""
    # Initialize report metadata
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_title = f"TruthLens Report ({source_type.capitalize()})"
    if source_url:
        report_title += f" - {source_url}"

    # 1) Summarize
    try:
        sum_raw = summarizer.summarize(text)["raw"]
    except Exception as e:
        st.error(f"Summarizer failed: {e}. Ensure OPENAI_API_KEY is valid.")
        st.stop()

    # 2) Extract claims
    claims_raw = []
    try:
        claims_raw = claim_extractor.extract_claims(text, k=8) or []
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
                    search_results += searcher.search_web(query, max_results=3)
                except Exception as e:
                    st.warning(f"Search failed for query '{query}': {e}. Skipping.")

        # Process search results
        source_entries = []
        snippets = []
        for result in search_results[:5]:
            url = result.get("url")
            if not url:
                continue
            trust_weight = scoring.trust_weight(url)
            source_entry = {
                "url": url,
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "trust_weight": trust_weight
            }
            source_entries.append(source_entry)
            snippets.append(f"{source_entry['title']} — {source_entry['snippet']}")
            global_sources.append(source_entry)

        # Assess claim
        try:
            assessment = fact_checker.assess_claim(claim_text, snippets)
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

    # Calculate scores
    truth_score = scoring.aggregate_truth_score(claim_assessments)
    stars = scoring.star_rating_from_quality(clarity=0.8, evidence=min(1.0, truth_score/100.0), bias=0.3)

    # Parse summary sections
    tldr, summary, deep = _parse_sections(sum_raw)

    # Generate markdown report
    md = f"""# {report_title}
**Generated:** {timestamp}  
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

# ─────────────────────────────────────────────────────────────────────────────
# UI

tab1, tab2 = st.tabs(["YouTube", "Text/Web"])

with tab1:
    url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
    analyze_button = st.button("Analyze YouTube", disabled=not bool(os.environ.get("YT_API_KEY")))
    
    if analyze_button and url.strip():
        # Basic YouTube URL validation
        if not re.match(r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]{11}", url):
            st.warning("Please enter a valid YouTube URL (e.g., https://www.youtube.com/watch?v=...).")
        else:
            with st.spinner("Fetching transcript…"):
                try:
                    text, metadata = transcript.fetch_transcript_youtube(url)
                    video_title = metadata.get("title", "Unknown Video")
                except Exception as e:
                    st.error(f"Failed to fetch transcript: {e}. Ensure YT_API_KEY is valid and the video has a public transcript.")
                    st.stop()
            
            with st.spinner("Analyzing…"):
                md = _run_pipeline(text, source_type="YouTube", source_url=url)
            st.success("Done.")
            st.markdown(md)
            st.download_button(
                "Download report (.md)",
                md,
                file_name=f"truthlens_youtube_{video_title.replace(' ', '_')}.md"
            )

with tab2:
    content = st.text_area("Paste text you have rights to use", height=220)
    if st.button("Analyze Text") and content.strip():
        with st.spinner("Analyzing…"):
            md = _run_pipeline(content, source_type="Text")
        st.success("Done.")
        st.markdown(md)
        st.download_button("Download report (.md)", md, file_name="truthlens_text_report.md")
