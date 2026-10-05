import os
import json
import time
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv(Path(__file__).parent / ".env")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL")  # optional

CACHE_FILE = Path(__file__).parent / "llm_cache.json"
_cache = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}


def _call_llm(contents, retries=3):
    models = [MODEL] + ([FALLBACK_MODEL] if FALLBACK_MODEL else [])
    last = None
    for model in models:
        for attempt in range(retries):
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config={"response_mime_type": "application/json", "temperature": 0},
                )
                return json.loads(resp.text)
            except errors.APIError as e:
                last = e
                code = getattr(e, "code", None)
                if code == 429:
                    break  # quota hit: retrying won't help, try the next model
                if code in (500, 503):
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise
            except json.JSONDecodeError as e:
                last = e
                continue
    raise RuntimeError(f"LLM unavailable: {last}")


def llm_json(prompt, image=None, mime=None):
    key_src = prompt.encode("utf-8") + (hashlib.sha256(image).digest() if image else b"")
    key = hashlib.sha256(key_src).hexdigest()
    if key in _cache:
        return _cache[key]
    contents = prompt if image is None else [types.Part.from_bytes(data=image, mime_type=mime), prompt]
    result = _call_llm(contents)
    _cache[key] = result
    CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
    return result


PROMPT = """You are helping fact-check a message forwarded on WhatsApp.
The message may be in English, Hindi, Punjabi, or Hinglish (Hindi/Punjabi written in Roman letters).

Do the following:
1. Detect the main language of the message.
2. Extract the single most checkable factual claim. Ignore greetings, emojis, and lines like "forward to everyone". If there is no checkable factual claim, set "claim" to null.
3. Write search queries for a fact-check database. Long queries return NOTHING, so keep them very short and use only the most distinctive terms (names, numbers, key nouns):
   - For each of English, Hindi (Devanagari), Punjabi (Gurmukhi): exactly 2 queries.
   - Query 1 must be exactly 2 words. Query 2 must be 3-4 words.

Return ONLY JSON in this exact shape:
{
  "language": "en|hi|pa|hinglish|other",
  "claim": "string or null",
  "queries": {"en": ["..",".."], "hi": ["..",".."], "pa": ["..",".."]}
}

Message:
"""

IMAGE_PROMPT = """You are helping fact-check a message forwarded on WhatsApp. The message is in the attached image, probably a chat screenshot or a forwarded poster. It may be in English, Hindi, Punjabi, or Hinglish.

Do the following:
1. Read the message text in the image. Ignore app UI, timestamps, contact names, and battery or signal icons.
2. Detect the main language of the message.
3. Extract the single most checkable factual claim. If there is no checkable factual claim, or the image has no readable text, set "claim" to null.
4. Write search queries for a fact-check database. Long queries return NOTHING, so keep them very short and use only the most distinctive terms (names, numbers, key nouns):
   - For each of English, Hindi (Devanagari), Punjabi (Gurmukhi): exactly 2 queries.
   - Query 1 must be exactly 2 words. Query 2 must be 3-4 words.

Return ONLY JSON in this exact shape:
{
  "extracted_text": "the message text you read from the image",
  "language": "en|hi|pa|hinglish|other",
  "claim": "string or null",
  "queries": {"en": ["..",".."], "hi": ["..",".."], "pa": ["..",".."]}
}
"""


def extract_claim(text: str) -> dict:
    return llm_json(PROMPT + text)


def extract_claim_from_image(image: bytes, mime: str) -> dict:
    return llm_json(IMAGE_PROMPT, image=image, mime=mime)


if __name__ == "__main__":
    print(json.dumps(extract_claim("5G टावर के पास रहने से कोरोना फैलता है, सबको भेजो!"), ensure_ascii=False, indent=2))