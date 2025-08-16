# ui/app_standalone.py
# ─────────────────────────────────────────────────────────────────────────────
# Make sure the repo root is searched BEFORE site-packages so our local
# ./app package wins over any third-party module named "app".
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# (optional safety) If some other "app" was already imported from site-packages,
# purge it so Python will import our local ./app package instead.
mod = sys.modules.get("app")
if mod is not None:
    mod_path = (getattr(mod, "__file__", "") or "").replace("\\", "/")
    if ROOT.replace("\\", "/") not in mod_path:
        del sys.modules["app"]

import re
from datetime import datetime
import streamlit as st

# Import services from the LOCAL package
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
    st.error(f"Failed to import local services: {e}\n"
             "Check that 'app/' exists and contains __init__.py files.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Streamlit page config
st.set_page_config(page_title="TruthLens — Standalone", layout="wide")
st.title("TruthLens — Standalone (no backend)")

# Sync Streamlit secrets → environment so pydantic-settings can read them.
def sync_env_from_secrets(required: list[str], optional: list[str]) -> None:
    try:
        secrets = st.secrets
    except Exception:
        secrets = {}
    # copy any present secrets to env (don’t overwrite existing env)
    for k in required + optional:
        if k in secrets and not os.environ.get(k):
            os.environ[k] = str(secrets[k])

    # enforce only the truly required ones
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        st.error("Missing required keys: " + ", ".join(missing))
        st.stop()

# Only OPENAI is required. TAVILY + YT are optional.
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
    st.markdown(
        "This app calls your service modules directly — "
        "**no FastAPI server required**."
    )

# ─────────────────────────────────────────────────────────────────────────────
# Helpers

def parse_sections(raw: str) -> tuple[list[str], str, str]:
    """Parse TL;DR, Executive Summary, and Deep Dive sections from raw text."""
    def extract(name: str) -> str:
        m = re.search(rf"{name}\s*:?\s*\n(.+?)(?:\n\n|$)", raw, flags=re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else ""
    tldr = [x.strip("- ").strip() for x in extract("TL;DR").split("\n") if x.strip()]
    summary = extract("Executive Summary") or "(no executive summary extracted)"
    deep = extract("Deep Dive") or "(no deep dive extracted)"
    return (tldr or ["(no TL;DR extracted)"], summary, deep)

def run_pipeline(text: str, source_type: str = "Text", source_url: str = "") -> str:
    """Summarize → extract claims → (optional) search → assess → score → markdown."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f"TruthLens Report ({source_type})"
    if source_url:
        title += f" — {source_url}"

    # 1) Summarize (requires OPENAI_API_KEY)
    try:
        sum_raw = summarizer.summarize(text)["raw"]
    except Exception as e:
        st.error(f"Summarizer failed. Ensure OPENAI_API_KEY is valid.\n\nDetails: {e}")
        st.stop()

    # 2) Claims
    try:
        claims_raw = claim_extractor.extract_claims(text, k=8) or []
    except Exception as e:
        st.warning(f"Claim extraction failed; continuing without claims. Details: {e}")
        claims_raw = []

    # 3) Search + assess per-claim (skip search if no provider)
    has_search = bool(os.environ.get("TAVILY_API_KEY"))
    claim_assessments, global_sources = [], []
    for c in claims_raw:
        ctext = c.get("text", "")
        qlist = (c.get("proposed_queries") or [ctext])[:3]

        results = []
        if has_search:
            for q in qlist:
                try:
                    results += searcher.search_web(q, max_results=3)
                except Exception:
                    # No provider configured or API error — skip silently
                    pass

        snippets, se_list = [], []
        for r in results[:5]:
            url = r.get("url")
            if not url:
                continue
            tw = scoring.trust_weight(url)
            se_list.append({"url": url, "title": r.get("title"), "snippet": r.get("snippet"), "trust_weight": tw})
            snippets.append(f"{r.get('title','')} — {r.get('snippet','')}")

        try:
            assess = fact_checker.assess_claim(ctext, snippets)
        except Exception as e:
            assess = {"support_score": 0.0, "contradiction_score": 0.0, "rationale": f"Assessment error: {e}"}

        claim_assessments.append({
            "claim": {"text": ctext, "snippet": c.get("snippet", ""), "proposed_queries": qlist},
            "support_score": float(assess.get("support_score") or 0.0),
            "contradiction_score": float(assess.get("contradiction_score") or 0.0),
            "sources": se_list,
            "rationale": assess.get("rationale", ""),
        })
        global_sources.extend(se_list)

    # 4) Score + stars
    truth = scoring.aggregate_truth_score(claim_assessments)
    stars = scoring.star_rating_from_quality(
        clarity=0.8,
        evidence=min(1.0, truth / 100.0),
        bias=0.3,
    )

    # 5) Compose report
    tldr, summary, deep = parse_sections(sum_raw)
    md = (
        f"# {title}\n"
        f"**Generated:** {timestamp}  \n"
        f"**Truth Score:** {truth:.1f}/100  \n"
        f"**Stars (Critical Style):** {stars:.1f}/5\n\n"
        "## TL;DR\n"
        "- " + "\n- ".join(tldr) + "\n\n"
        "## Executive Summary\n"
        f"{summary}\n\n"
        "## Deep Dive\n"
        f"{deep}\n\n"
        "## Claims & Evidence\n"
    )
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
    if st.button("Analyze YouTube"):
        if not url.strip():
            st.warning("Please paste a YouTube URL.")
        elif not re.match(r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]{11}", url):
            st.warning("Please enter a valid YouTube URL.")
        else:
            with st.spinner("Fetching transcript…"):
                try:
                    # Expect (text, timed) from transcript service
                    text, _timed = transcript.fetch_transcript_youtube(url)
                except Exception as e:
                    text = None
                    st.error(f"Transcript fetch failed: {e}")
            if not text:
                st.error("No public transcript found. Try another video or paste text in the Text/Web tab.")
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

