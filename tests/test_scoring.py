from app.services.scoring import aggregate_truth_score

def test_aggregate_truth_score_empty():
    assert aggregate_truth_score([]) == 50.0
