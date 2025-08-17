def trust_weight(url: str) -> float:
    return 0.5

def aggregate_truth_score(assessments: list) -> float:
    return 50.0

def star_rating_from_quality(clarity: float, evidence: float, bias: float) -> float:
    return 3.0
