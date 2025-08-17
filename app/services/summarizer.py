from .llm import llm_complete

SUMMARY_PROMPT = """You are an analyst.
Given CONTENT below, produce:
1) TL;DR: 5–8 bullets.
2) Executive Summary (300–600 words).
3) Deep Dive: structure, arguments, rhetorical techniques; 5–10 bullets.

Return sections titled exactly: TL;DR, Executive Summary, Deep Dive.

CONTENT:
{content}"""

def summarize(content: str) -> dict:
    out = llm_complete(SUMMARY_PROMPT.format(content=content))
    return {"raw": out}
