from .llm import llm_complete
from ..config import settings

CLAIM_PROMPT = """Extract up to {k} factual claims from CONTENT.
For each claim, return JSON with fields:
- text
- snippet (<=140 chars from content)
- proposed_queries (array of 1–3 web search queries)

Only include verifiable factual statements, not opinions.

CONTENT:
{content}
"""

def extract_claims(content: str, k: int = 8):
    import json
    raw = llm_complete(CLAIM_PROMPT.format(content=content, k=k))
    try:
        data = json.loads(raw)
        return data
    except Exception:
        # fallback: very simple parse; in real use, re-ask LLM for valid JSON
        return []
