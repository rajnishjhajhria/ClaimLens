import os
import requests
from dotenv import load_dotenv
import time

load_dotenv()

API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
API_KEY = os.getenv("FACTCHECK_API_KEY")


RETRY_STATUSES = {429, 500, 502, 503, 504}

def search_claims(query, language_code=None, max_age_days=None, page_size=10, retries=3):
    params = {"query": query, "key": API_KEY, "pageSize": page_size}
    if language_code:
        params["languageCode"] = language_code
    if max_age_days:
        params["maxAgeDays"] = max_age_days

    for attempt in range(retries + 1):
        try:
            resp = requests.get(API_URL, params=params, timeout=30)
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Fact Check API network error: {e}")
        if resp.ok:
            break
        if resp.status_code in RETRY_STATUSES and attempt < retries:
            time.sleep(2 ** attempt)
            continue
        raise RuntimeError(f"Fact Check API error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    results = []
    for claim in data.get("claims", []):
        for review in claim.get("claimReview", []):
            results.append({
                "claim": claim.get("text"),
                "claimant": claim.get("claimant"),
                "publisher": review.get("publisher", {}).get("name"),
                "rating": review.get("textualRating"),
                "title": review.get("title"),
                "url": review.get("url"),
                "date": review.get("reviewDate"),
                "language": review.get("languageCode"),
            })
    return results


if __name__ == "__main__":
    tests = [
        ("5g causes covid", "en"),
        ("5g कोविड", "hi"),
        ("ਕੋਰੋਨਾ ਵੈਕਸੀਨ", "pa"),
    ]
    for q, lang in tests:
        print(f"\n=== {q} ({lang}) ===")
        for r in search_claims(q, lang)[:3]:
            print(f"- [{r['rating']}] {r['publisher']} | {r['language']} | {r['url']}")