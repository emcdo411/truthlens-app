from .llm import llm_complete

def assess_claim(claim: str, snippets: list) -> dict:
    prompt = f"Assess the following claim based on these snippets:\nClaim: {claim}\nSnippets:\n" + "\n".join(snippets)
    response = llm_complete(prompt)
    return {"support_score": 0.5, "contradiction_score": 0.2, "rationale": "Sample assessment"}
