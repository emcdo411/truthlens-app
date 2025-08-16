from typing import Literal, Optional, List
from . import summarizer
from ..config import settings
import os

# Simple provider-agnostic wrapper (OpenAI default)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

def llm_complete(prompt: str, model: Optional[str] = None) -> str:
    if settings.OPENAI_API_KEY and OpenAI:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        mdl = model or "gpt-4.1-mini"
        resp = client.responses.create(model=mdl, input=prompt)
        return resp.output_text
    # Fallback: raise informative error
    raise RuntimeError("No LLM provider configured. Set OPENAI_API_KEY (or extend llm.py).")
