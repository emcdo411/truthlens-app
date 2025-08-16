from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class Claim(BaseModel):
    text: str
    snippet: Optional[str] = None
    confidence: Optional[float] = None
    proposed_queries: List[str] = []

class SourceEvidence(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    snippet: Optional[str] = None
    trust_weight: float

class ClaimAssessment(BaseModel):
    claim: Claim
    support_score: float  # 0-1
    contradiction_score: float  # 0-1
    sources: List[SourceEvidence]
    rationale: str

class AnalysisResult(BaseModel):
    tldr: List[str]
    tldw: Optional[List[str]] = None
    summary: str
    deep_dive: str
    claims: List[ClaimAssessment]
    truth_score: float  # 0-100
    star_rating: float  # 1-5
    sources: List[SourceEvidence]
    markdown_report: str
    json_report: dict
