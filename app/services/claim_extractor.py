from .llm import llm_complete

def extract_claims(text: str, k: int = 8) -> list:
    prompt = f"Extract up to {k} factual claims from the following text:\n\n{text}"
    response = llm_complete(prompt)
    # Placeholder: Parse response into list of claims
    return [{"text": "Sample claim", "snippet": "Sample text", "proposed_queries": ["sample search"]}]
