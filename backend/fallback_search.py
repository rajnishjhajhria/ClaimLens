import os
import requests
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
TAVILY_KEY = os.getenv("TAVILY_API_KEY")

FACTCHECK_DOMAINS = [
    "altnews.in", "boomlive.in", "vishvasnews.com", "factly.in", "thequint.com",
    "factcheck.afp.com", "newschecker.in", "digiteye.in", "thip.media",
    "firstcheck.in", "fullfact.org", "medicaldialogues.in", "politifact.com",
]


def tavily_search(claim, max_results=8):
    if not TAVILY_KEY:
        print("  TAVILY_API_KEY missing, skipping fallback")
        return []
    resp = requests.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {TAVILY_KEY}"},
        json={
            "query": f"fact check: {claim}",
            "include_domains": FACTCHECK_DOMAINS,
            "max_results": max_results,
        },
        timeout=30,
    )
    resp.raise_for_status()
    out = []
    for r in resp.json().get("results", []):
        out.append({
            "claim": r.get("content"),
            "claimant": None,
            "publisher": urlparse(r["url"]).netloc,
            "rating": None,
            "title": r.get("title"),
            "url": r["url"],
            "date": None,
            "language": None,
            "source": "web search",
        })
    return out