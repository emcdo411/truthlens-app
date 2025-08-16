from typing import Dict, List
from .llm import llm_complete

ASSESS_PROMPT = """You are a strict fact-checking assistant.
Given a CLAIM and a list of WEB SNIPPETS, score:
- support_score (0-1): how strongly snippets support claim
- contradiction_score (0-1): how strongly snippets contradict claim
- rationale: brief explanation (<=120 words)

Return a compact JSON with keys: support_score, contradiction_score, rationale.

CLAIM: {claim}
SNIPPETS:
{snippets}
"""

def assess_claim(claim_text: str, snippets: List[str]) -> Dict:
    import json
    joined = "\n---\n".join(snippets[:8])
    raw = llm_complete(ASSESS_PROMPT.format(claim=claim_text, snippets=joined))
    try:
        return json.loads(raw)
    except Exception:
        return {"support_score": 0.0, "contradiction_score": 0.0, "rationale": "Parse error"}
