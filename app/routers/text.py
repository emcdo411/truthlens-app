from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from ..services import summarizer, claim_extractor, searcher, fact_checker, scoring

router = APIRouter(prefix="/analyze", tags=["text"])

class TextIn(BaseModel):
    content: str

@router.post("/text")
def analyze_text(body: TextIn):
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="No content provided.")

    # 1) Summaries
    sum_raw = summarizer.summarize(content)["raw"]

    # 2) Claims → search → assess
    claims_raw = claim_extractor.extract_claims(content, k=8) or []
    claim_assessments, global_sources = [], []

    import json
    def safe(val, default):
        return val if val is not None else default

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
            if not url: 
                continue
            tw = scoring.trust_weight(url)
            se_list.append({"url": url, "title": r.get("title"), "snippet": r.get("snippet"), "trust_weight": tw})
            snippets.append(f"{r.get('title','')} — {r.get('snippet','')}")

        assess = fact_checker.assess_claim(c.get("text",""), snippets)
        item = {
            "claim": {
                "text": c.get("text",""),
                "snippet": c.get("snippet"),
                "proposed_queries": qlist
            },
            "support_score": safe(assess.get("support_score"), 0.0),
            "contradiction_score": safe(assess.get("contradiction_score"), 0.0),
            "sources": se_list,
            "rationale": assess.get("rationale","")
        }
        claim_assessments.append(item)
        global_sources.extend(se_list)

    truth = scoring.aggregate_truth_score(claim_assessments)
    stars = scoring.star_rating_from_quality(clarity=0.8, evidence=min(1.0, truth/100.0), bias=0.3)

    # Parse sections from summarizer output
    import re
    def section(name: str):
        m = re.search(rf"{name}\s*:?\s*\n(.+?)(?:\n\n|$)", sum_raw, flags=re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else ""

    tldr = [x.strip("- ").strip() for x in section("TL;DR").split("\n") if x.strip()]
    summary = section("Executive Summary")
    deep = section("Deep Dive")

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

    return {
        "tldr": tldr,
        "tldw": None,
        "summary": summary,
        "deep_dive": deep,
        "claims": claim_assessments,
        "truth_score": truth,
        "star_rating": stars,
        "sources": global_sources[:20],
        "markdown_report": md,
        "json_report": {}
    }

