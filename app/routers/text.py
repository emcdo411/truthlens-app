from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..services import summarizer, claim_extractor, searcher, fact_checker, scoring
from ..models.schemas import AnalysisResult, ClaimAssessment, Claim, SourceEvidence
from typing import List

router = APIRouter(prefix="/analyze", tags=["text"])

class TextIn(BaseModel):
    content: str

@router.post("/text", response_model=AnalysisResult)
def analyze_text(body: TextIn):
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="No content provided.")
    # Summaries
    s = summarizer.summarize(content)["raw"]

    # Claims
    claims_raw = claim_extractor.extract_claims(content, k=8)
    claim_assessments = []
    global_sources = []

    for c in claims_raw:
        qlist = c.get("proposed_queries", []) or [c["text"]]
        results = []
        for q in qlist:
            try:
                results += searcher.search_web(q, max_results=3)
            except Exception:
                pass
        snippets = []
        se_list = []
        for r in results[:5]:
            if not r.get("url"): continue
            tw = scoring.trust_weight(r["url"])
            se_list.append(SourceEvidence(url=r["url"], title=r.get("title"), snippet=r.get("snippet"), trust_weight=tw))
            snippets.append(f"{r.get('title','')} — {r.get('snippet','')}")
        assess = fact_checker.assess_claim(c["text"], snippets)
        claim_assessments.append(ClaimAssessment(
            claim=Claim(text=c["text"], snippet=c.get("snippet"), proposed_queries=qlist),
            support_score=assess["support_score"],
            contradiction_score=assess["contradiction_score"],
            sources=se_list,
            rationale=assess["rationale"]
        ))
        global_sources.extend(se_list)

    truth = scoring.aggregate_truth_score([a.dict() for a in claim_assessments])
    # naive star rating proxy
    stars = scoring.star_rating_from_quality(clarity=0.8, evidence=min(1.0, truth/100), bias=0.3)

    # very simple TL;DR/Deep Dive extraction from s (already sectioned)
    import re
    def section(name: str):
        m = re.search(rf"{name}\s*:?\s*\n(.+?)(?:\n\n|$)", s, flags=re.IGNORECASE | re.DOTALL)
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
        [f"- **Claim:** {a.claim.text}\n  - Support: {a.support_score:.2f}, Contra: {a.contradiction_score:.2f}\n  - Rationale: {a.rationale}\n  - Sources: " +
         ", ".join([f"[{s.title or s.url}]({s.url})" for s in a.sources]) for a in claim_assessments]
    )

    return AnalysisResult(
        tldr=tldr,
        tldw=None,
        summary=summary,
        deep_dive=deep,
        claims=claim_assessments,
        truth_score=truth,
        star_rating=stars,
        sources=global_sources[:20],
        markdown_report=md,
        json_report={}
    )
