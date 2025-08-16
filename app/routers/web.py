from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from ..models.schemas import AnalysisResult
from .text import analyze_text, TextIn

router = APIRouter(prefix="/analyze", tags=["web"])

class WebIn(BaseModel):
    url: HttpUrl
    # The app intentionally requires user to paste extracted text to avoid scraping copyrighted content
    extracted_text: str

@router.post("/web", response_model=AnalysisResult)
def analyze_web(body: WebIn):
    if not body.extracted_text.strip():
        raise HTTPException(status_code=400, detail="Provide extracted text (public domain or your own).")
    return analyze_text(TextIn(content=body.extracted_text))
