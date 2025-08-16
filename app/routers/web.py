from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from .text import analyze_text, TextIn

router = APIRouter(prefix="/analyze", tags=["web"])

class WebIn(BaseModel):
    url: HttpUrl
    extracted_text: str

@router.post("/web")
def analyze_web(body: WebIn):
    txt = (body.extracted_text or "").strip()
    if not txt:
        raise HTTPException(status_code=400, detail="Provide extracted text you have rights to use.")
    return analyze_text(TextIn(content=txt))
