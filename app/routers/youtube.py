from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from ..services import transcript
from .text import analyze_text, TextIn

router = APIRouter(prefix="/analyze", tags=["youtube"])

class YTIn(BaseModel):
    url: HttpUrl

@router.post("/youtube")
def analyze_youtube(body: YTIn):
    text, timed = transcript.fetch_transcript_youtube(str(body.url))
    if not text:
        raise HTTPException(status_code=404, detail="No public transcript found. Paste text instead.")
    return analyze_text(TextIn(content=text))

