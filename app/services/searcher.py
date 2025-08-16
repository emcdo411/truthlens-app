from typing import List, Dict
from ..config import settings

def search_web(query: str, max_results: int = 5) -> List[Dict]:
    """
    Implement a provider (Tavily / Serper / DuckDuckGo).
    For illustration, we show Tavily. Replace with your choice.
    """
    import requests, os
    if settings.TAVILY_API_KEY:
        r = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": settings.TAVILY_API_KEY, "query": query, "max_results": max_results}
        )
        r.raise_for_status()
        items = r.json().get("results", [])
        return [{"url": i.get("url"), "title": i.get("title"), "snippet": i.get("content")} for i in items]
    raise RuntimeError("No search provider configured. Set TAVILY_API_KEY or implement alternative.")
