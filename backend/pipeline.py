from factcheck_api import search_claims
from claim_extractor import extract_claim, extract_claim_from_image, llm_json
import os
import re
from reranker import judge_embedding
from rank import add_rank_scores, sort_key

JUDGE_MODE = os.getenv("JUDGE_MODE", "embedding")  # "embedding" or "llm"

# Results found by the Tavily web-search fallback have no rating and no stated claim, and that path was not
# evaluated, so by default they are shown as "related" and never as a match. Set TAVILY_CAN_MATCH=1 to allow matches.
TAVILY_CAN_MATCH = os.getenv("TAVILY_CAN_MATCH", "0") == "1"

LANG_KEYS = ["en", "hi", "pa"]
MAX_CANDIDATES = 20
MAX_SHOWN = 5

JUDGE_PROMPT = """You compare a claim from a WhatsApp forward with fact-checks found by a search.
For each candidate, decide:
- "same": the fact-check debunks the same rumor the forward spreads, even if it is about a different instance of it (a different video, person, political party, date, amount or threshold).
- "related": same topic, but about a different rumor (a different remedy or mechanism, or a company instead of a political actor).
- "unrelated": a different topic.

Candidates may be in English, Hindi or Punjabi. Judge by meaning, not exact words.
Return ONLY a JSON list like [{"i": 0, "verdict": "same"}, ...] with one entry per candidate.
"""


def run_queries(queries_by_lang, seen):
    for lang in LANG_KEYS:
        for q in queries_by_lang.get(lang, []):
            try:
                results = search_claims(q, lang)
            except Exception as e:
                print(f"  search failed for {q!r}: {e}")
                continue
            print(f"  {lang}: {q!r} -> {len(results)} results")
            for r in results:
                if r["url"] and r["url"] not in seen:
                    seen[r["url"]] = r


def gather_candidates(queries, claim):
    seen = {}
    run_queries(queries, seen)
    if len(seen) < 3:
        print("  few results, retrying with shorter queries")
        short = {
            lang: list({" ".join(q.split()[:2]) for q in qs})
            for lang, qs in queries.items()
        }
        run_queries(short, seen)
    if len(seen) < 3:
        print("  still few results, trying Tavily on fact-check sites")
        try:
            from fallback_search import tavily_search
            for r in tavily_search(claim):
                seen.setdefault(r["url"], r)
        except Exception as e:
            print("  tavily failed:", e)
    return list(seen.values())[:MAX_CANDIDATES]


def judge(claim, candidates):
    items = [
        {
            "i": i,
            "fact_checked_claim": (c["claim"] or "")[:300],
            "title": (c["title"] or "")[:200],
        }
        for i, c in enumerate(candidates)
    ]
    import json
    data = llm_json(
        f"{JUDGE_PROMPT}\nUSER CLAIM: {claim}\n\nCANDIDATES:\n"
        + json.dumps(items, ensure_ascii=False)
    )
    if isinstance(data, dict):
        data = data.get("judgments") or data.get("results") or []
    return {d["i"]: d["verdict"] for d in data}

def get_verdicts(claim, candidates):
    if JUDGE_MODE == "llm":
        try:
            return judge(claim, candidates), "llm"
        except Exception as e:
            print("  LLM judge failed, using embeddings instead:", e)
    return judge_embedding(claim, candidates), "embedding"

def fix_language(ext, source_text=""):
    """Decide the language from the script of the message itself; the model's label is only used for Latin text."""
    src = source_text or ext.get("extracted_text") or ""
    deva = len(re.findall(r"[\u0900-\u097F]", src))
    gurm = len(re.findall(r"[\u0A00-\u0A7F]", src))
    letters = len(re.findall(r"[^\W\d_]", src)) or 1
    if (deva + gurm) / letters >= 0.3:
        ext["language"] = "pa" if gurm > deva else "hi"
    elif src.strip() and ext.get("language") in ("hi", "pa"):
        ext["language"] = "hinglish"  # Hindi or Punjabi written in Roman letters
    return ext


def check_forward(text=None, image=None, mime=None):
    ext = extract_claim_from_image(image, mime) if image else extract_claim(text)
    fix_language(ext, text or "")
    if not ext.get("claim"):
        return {"status": "no_claim", "extraction": ext}

    candidates = gather_candidates(ext["queries"], ext["claim"])
    if not candidates:
        return {"status": "no_match", "extraction": ext, "candidates_found": 0}

    try:
        verdicts, judged_by = get_verdicts(ext["claim"], candidates)
    except Exception as e:
        print("  judge failed:", e)
        return {
            "status": "unjudged",
            "extraction": ext,
            "candidates_found": len(candidates),
            "unjudged": candidates[:MAX_SHOWN],
        }
    def is_web(c):
        return c.get("source") == "web search"

    def is_match(i, c):
        return verdicts.get(i) == "same" and (TAVILY_CAN_MATCH or not is_web(c))

    matches = [c for i, c in enumerate(candidates) if is_match(i, c)]
    # a web-search result the judge called "same" is kept, but only as related
    related = [c for i, c in enumerate(candidates)
               if not is_match(i, c) and verdicts.get(i) in ("related", "same")]
    # closest to the user's claim first (the same ordering whichever judge was used)
    add_rank_scores(ext["claim"], matches + related)
    matches.sort(key=sort_key, reverse=True)
    related.sort(key=sort_key, reverse=True)

    return {
        "status": "match" if matches else "no_match",
        "extraction": ext,
        "judged_by": judged_by,
        "candidates_found": len(candidates),
        "matches_total": len(matches),
        "matches": matches[:MAX_SHOWN],
        "related": related[:5],
    }


def show(result):
    print("STATUS:", result["status"])
    print("CLAIM :", result["extraction"].get("claim"))
    print("CANDIDATES FOUND:", result.get("candidates_found", 0),
          "| MATCHES TOTAL:", result.get("matches_total", 0))
    for label in ("matches", "related"):
        for r in result.get(label, []):
            print(f"  [{label.upper()}] [{(r['rating'] or '')[:40]}] {r['publisher']} | {r['language']} | {(r['date'] or '')[:10]} | {r['url']}")


if __name__ == "__main__":
    samples = [
        "🚨 FORWARD TO ALL 🚨 Drinking hot water with lemon every morning cures cancer, doctors are hiding this! Share with 10 groups",
        "अगर आप 5G टावर के पास रहते हैं तो कोरोना फैलता है, सरकार ने यह बात छुपाई है। सबको भेजो!",
        "Bhai ye forward kar do, kal se sabhi ATM se 500 ke note band ho jayenge, RBI ne order nikala hai",
        "Eating exactly 7 almonds every Tuesday doubles your IQ, scientists confirmed",
        "Hi all, my cousin's wedding is this Sunday 5pm, please come with family",
    ]
    for s in samples:
        print("\n" + "=" * 60)
        try:
            show(check_forward(s))
        except Exception as e:
            print("ERROR:", e)