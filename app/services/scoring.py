from typing import List, Dict
TRUST_TABLE = [
    (".gov", 1.0),
    (".edu", 0.9),
    ("nature.com", 0.95),
    ("science.org", 0.95),
    ("nejm.org", 0.95),
    ("who.int", 0.95),
    ("un.org", 0.9),
    ("bbc.com", 0.8),
    ("reuters.com", 0.85),
    ("apnews.com", 0.82),
]

def trust_weight(url: str) -> float:
    u = url.lower()
    for domain, w in TRUST_TABLE:
        if domain in u or u.endswith(domain):
            return w
    return 0.6  # default

def aggregate_truth_score(claim_assessments: List[Dict]) -> float:
    """
    Aggregate claim-level support/contradiction into a 0–100 score.
    """
    if not claim_assessments:
        return 50.0
    total = 0.0
    for ca in claim_assessments:
        s = ca.get("support_score", 0.0)
        c = ca.get("contradiction_score", 0.0)
        # Simple rubric: support - contradiction, scaled
        total += max(0.0, s - 0.5*c)
    avg = total / len(claim_assessments)
    return round(avg * 100, 2)

def star_rating_from_quality(clarity: float, evidence: float, bias: float) -> float:
    """
    Compute 1–5 star rating; clarity/evidence positive; bias negative.
    """
    base = (0.5*clarity + 0.5*evidence) - 0.2*bias
    stars = 1 + 4*max(0.0, min(1.0, base))
    return round(stars, 1)
