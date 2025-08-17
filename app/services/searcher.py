import os
from tavily import TavilyClient

def search_web(query: str, max_results: int = 3) -> list:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return [{"url": "https://example.com", "title": "Example Page", "snippet": "Sample result"}]
    client = TavilyClient(api_key=api_key)
    try:
        results = client.search(query, max_results=max_results)
        return [{"url": r["url"], "title": r["title"], "snippet": r["content"]} for r in results["results"]]
    except Exception as e:
        print(f"Search error: {e}")
        return []
