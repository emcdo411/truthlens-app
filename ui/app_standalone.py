import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services import summarizer, claim_extractor, searcher, fact_checker, scoring, transcript
import streamlit as st
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st

# Load your services directly (standalone mode: no FastAPI needed)
from app.services import (
    summarizer,
    claim_extractor,
    searcher,
    fact_checker,
    scoring,
    transcript,
)

# ─────────────────────────────────────────────────────────────────────────────
# Streamlit page config
st.set_page_config(page_title="TruthLens", layout="wide")
st.title("TruthLens — Standalone")

# Copy selected Streamlit secrets into environment variables so that
# app.config.Settings() (pydantic-settings) picks them up.
def _sync_env_from_secrets(keys):
    try:
        secrets = st.secrets  # Streamlit injects this on Cloud
    except Exception:
        secrets = {}
    for k in keys:
        if k in secrets and not os.environ.get(k):
            os.environ[k] = str(secrets[k])

_sync_env_from_secrets(["OPENAI_API_KEY", "TAVILY_API_KEY", "YT_API_KEY"])

# Small helper: show whether keys are present
def _key_status():
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_tavily = bool(os.environ.get("TAVILY_API_KEY"))
    st.caption(
        f"OpenAI key: {'✅' if has_openai else '❌'} · "
        f"Tavily key (optional): {'✅' if has_tavily else '⚪️ optional'}"
    )

with st.sidebar:
    st.subheader("Runtime")
    _key_status()
    st.markdown(
        "This **standalone** app calls your service modules directly — "
        "no external FastAPI backend required."
    )

# ─────────────────────────────────────────────────────────────────────────────
# Utilities

def _parse_sections(raw: str):
    """Pick TL;DR / Executive Summary / Deep Dive from the summarizer output."""
    import re
    def section(name: str):
        m = re.search(rf"{name}\s*:?\s*\n(.+?)(?:\n\n|$)", raw, flags=re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else ""
    tldr = [x.strip("- ").strip() for x in section("TL;DR").split("\n") if x.strip()]
    summary = section("Executive Summary")
    deep = section("Deep Dive")
    return tldr, summary, deep

def _run_pipeline(text: str) -> str:
    """
    Core pipeline:
      1) Summarize content
      2) Extract claims
      3) Search web for snippets (if TAVILY_API_KEY present)
      4) LLM fact-check support/contradiction
      5) Aggregate Truth Score, compose Markdown report
    Returns a Markdown string.
    """
    # 1) Summaries (requires OPENAI_API_KEY)
    try:
        sum_raw = summarizer.summarize(text)["raw"]
    except Exception as e:
        st.error(
            "Summarizer failed. Make sure `OPENAI_API_KEY` is configured. "
            f"\n\nDetails: {e}"
        )
        st.stop()

    # 2) Claims
    try:
        claims_raw = claim_extractor.extract_claims(text, k=8) or []
    except Exception as e:
        st.warning(f"Claim extraction failed; continuing without claims. Details: {e}")
        claims_raw = []

    # 3–4) For each claim, search & assess
    claim_assessments, global_sources = [], []
    for c in claims_raw:
        qlist = c.get("proposed_queries") or [c.get("text", "")]
        results = []
        for q in qlist[:3]:
            try:
                # Will raise if no search provider configured; we just skip evidence in that case
                results += searcher.search_web(q, max_results=3)
            except Exception:
                # no TAVILY_API_KEY or provider error — skip silently, keep pipeline running
                pass

        snippets, se_list = [], []
        for r in results[:5]:
            url = r.get("url")
            if not url:
                continue
            tw = scoring.trust_weight(url)
            se_list.append(
                {"url": url, "title": r.get("title"), "snippet": r.get("snippet"), "trust_weight": tw}
            )
            snippets.append(f"{r.get('title','')} — {r.get('snippet','')}")

        try:
            assess = fact_checker.assess_claim(c.get("text", ""), snippets)
        except Exception as e:
            assess = {"support_score": 0.0, "contradiction_score": 0.0, "rationale": f"Assessment error: {e}"}

        item = {
            "claim": {
                "text": c.get("text", ""),
                "snippet": c.get("snippet"),
                "proposed_queries": qlist
            },
            "support_score": float(assess.get("support_score") or 0.0),
            "contradiction_score": float(assess.get("contradiction_score") or 0.0),
            "sources": se_list,
            "rationale": assess.get("rationale", "")
        }
        claim_assessments.append(item)
        global_sources.extend(se_list)

    # 5) Aggregate Truth Score + stars
    truth = scoring.aggregate_truth_score(claim_assessments)
    stars = scoring.star_rating_from_quality(
        clarity=0.8,
        evidence=min(1.0, truth / 100.0),
        bias=0.3
    )

    tldr, summary, deep = _parse_sections(sum_raw)

    md = f"""# TruthLens Report
**Truth Score:** {truth}/100  
**Stars (Critical Style):** {stars}/5

## TL;DR
- """ + "\n- ".join(tldr or ["(no TL;DR extracted)"]) + f"""

## Executive Summary
{summary or '(no executive summary extracted)'}

## Deep Dive
{deep or '(no deep dive extracted)'}

## Claims & Evidence
""" + (
        "\n".join(
            [
                f"- **Claim:** {a['claim']['text']}\n"
                f"  - Support: {a['support_score']:.2f}, Contra: {a['contradiction_score']:.2f}\n"
                f"  - Rationale: {a['rationale']}\n"
                f"  - Sources: " + (
                    ", ".join([f"[{s.get('title') or s.get('url')}]({s.get('url')})" for s in a['sources']])
                    if a["sources"] else "(none)"
                )
                for a in claim_assessments
            ]
        )
        if claim_assessments
        else "_No claims extracted or evidence search unavailable._"
    )

    return md

# ─────────────────────────────────────────────────────────────────────────────
# UI

tab1, tab2 = st.tabs(["YouTube", "Text/Web"])

with tab1:
    url = st.text_input("YouTube URL")
    if st.button("Analyze YouTube"):
        if not url.strip():
            st.warning("Please paste a YouTube URL.")
        else:
            with st.spinner("Fetching transcript…"):
                try:
                    text, _timed = transcript.fetch_transcript_youtube(url)
                except Exception as e:
                    text, _timed = None, None
                    st.error(f"Transcript fetch failed: {e}")
            if not text:
                st.error("No public transcript found. Try a different video, or paste text in the Text/Web tab.")
            else:
                with st.spinner("Analyzing…"):
                    md = _run_pipeline(text)
                st.success("Done.")
                st.markdown(md)
                st.download_button("Download report (.md)", md, file_name="truthlens_report.md")

with tab2:
    content = st.text_area("Paste text you have rights to use", height=220)
    if st.button("Analyze Text"):
        if not content.strip():
            st.warning("Please paste some text.")
        else:
            with st.spinner("Analyzing…"):
                md = _run_pipeline(content)
            st.success("Done.")
            st.markdown(md)
            st.download_button("Download report (.md)", md, file_name="truthlens_report.md")

