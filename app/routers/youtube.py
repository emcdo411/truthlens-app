from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from ..services import transcript, summarizer
from ..models.schemas import AnalysisResult

router = APIRouter(prefix="/analyze", tags=["youtube"])

class YTIn(BaseModel):
    url: HttpUrl

@router.post("/youtube", response_model=AnalysisResult)
def analyze_youtube(body: YTIn):
    text, timed = transcript.fetch_transcript_youtube(str(body.url))
    if not text:
        raise HTTPException(status_code=404, detail="No public transcript found. Enable local transcription or provide text.")
    s = summarizer.summarize(text)["raw"]
    # naive TL;DW from timed segments
    tldw = []
    for seg, start in (timed or [])[:12]:
        mm = int(start // 60); ss = int(start % 60)
        tldw.append(f"[{mm:02d}:{ss:02d}] {seg}")

    # Reuse text router by calling its logic would be better; here keep minimal:
    from .text import analyze_text, TextIn
    return analyze_text(TextIn(content=text))
