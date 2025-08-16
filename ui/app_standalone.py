# Ensure repo root is on sys.path (needed on Streamlit Cloud)
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services import summarizer, claim_extractor, searcher, fact_checker, scoring, transcript

st.set_page_config(page_title="TruthLens", layout="wide")
st.title("TruthLens (Standalone)")

with st.sidebar:
    st.markdown("### Keys & Settings")
    st.write("Set secrets in Streamlit Cloud → App settings → Secrets.")
    st.caption("Required: OPENAI_API_KEY, TAVILY_API_KEY")
    st.code("OPENAI_API_KEY=...\nTAVILY_API_KEY=...")

tab1, tab2 = st.tabs(["YouTube", "Text/Web"])

def run_pipeline(text: str):
    # Summarize
    sum_raw = summarizer.summarize(text)["raw"]
    # Claims
    claims_raw = claim_extractor.extract_claims(text, k=8) or []
    claim_assessments, global_sources = [], []
    for c in claims_raw:
        qlist = c.get("proposed_queries") or [c.get("text","")]
        results = []
        for q in qlist[:3]:
            try:
                results += searcher.search_web(q, max_results=3)
            except Exception:
                pass
        snippets, se_list = [], []
        for r in results[:5]:
            url = r.get("url")
            if not url: continue
            tw = scoring.trust_weight(url)
            se_list.append({"url": url, "title": r.get("title"), "snippet": r.get("snippet"), "trust_weight": tw})
            snippets.append(f"{r.get('title','')} — {r.get('snippet','')}")
        assess = fact_checker.assess_claim(c.get("text",""), snippets)
        claim_assessments.append({
            "claim": {"text": c.get("text",""), "snippet": c.get("snippet"), "proposed_queries": qlist},
            "support_score": assess.get("support_score",0.0),
            "contradiction_score": assess.get("contradiction_score",0.0),
            "sources": se_list,
            "rationale": assess.get("rationale","")
        })
        global_sources.extend(se_list)

    truth = scoring.aggregate_truth_score(claim_assessments)
    stars = scoring.star_rating_from_quality(clarity=0.8, evidence=min(1.0, truth/100.0), bias=0.3)

    import re
    def section(name: str):
        m = re.search(rf"{name}\s*:?\s*\n(.+?)(?:\n\n|$)", sum_raw, flags=re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else ""
    tldr = [x.strip("- ").strip() for x in section("TL;DR").split("\n") if x.strip()]
    summary = section("Executive Summary"); deep = section("Deep Dive")

    md = f"""# TruthLens Report
**Truth Score:** {truth}/100  
**Stars (Critical Style):** {stars}/5

## TL;DR
- """ + "\n- ".join(tldr) + f"""

## Executive Summary
{summary}

## Deep Dive
{deep}

## Claims & Evidence
""" + "\n".join(
        [f"- **Claim:** {a['claim']['text']}\n  - Support: {a['support_score']:.2f}, Contra: {a['contradiction_score']:.2f}\n  - Rationale: {a['rationale']}\n  - Sources: " +
         ", ".join([f"[{s.get('title') or s.get('url')}]({s.get('url')})" for s in a['sources']]) for a in claim_assessments]
    )
    return md

with tab1:
    url = st.text_input("YouTube URL")
    if st.button("Analyze YouTube"):
        text, _ = transcript.fetch_transcript_youtube(url)
        if not text:
            st.error("No public transcript found. Try a different video or paste text in the Text/Web tab.")
        else:
            st.markdown(run_pipeline(text))

with tab2:
    content = st.text_area("Paste text you have rights to use", height=220)
    if st.button("Analyze Text"):
        if not content.strip():
            st.warning("Please paste some text.")
        else:
            st.markdown(run_pipeline(content))
