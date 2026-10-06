from factcheck_api import search_claims
from claim_extractor import extract_claim, extract_claim_from_image, llm_json
import os
import re
from reranker import judge_embedding
from rank import add_rank_scores, sort_key
from reranker import RELATED_T

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


LISTING_URL_RE = re.compile(r"/(topic|topics|tag|tags|category|categories|author|authors|search)/", re.I)
LISTING_TITLE_RE = re.compile(r"(top stories|articles, photos|news, photos|photos, videos)", re.I)


def is_listing_page(c):
    """Topic, tag and search pages are not fact-checks, whatever words they contain."""
    return bool(LISTING_URL_RE.search(c.get("url") or "") or LISTING_TITLE_RE.search(c.get("title") or ""))


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
    return [c for c in seen.values() if not is_listing_page(c)][:MAX_CANDIDATES]


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


# ---------- personal notifications (loan / bank / credit alerts) ----------
# "Your loan amount on account xxx8898 has increased" is a message to one person, not a rumour that
# fact-checkers review. The rule is deliberately narrow: all three parts must be present.
MASKED_ID_RE = re.compile(r"(?:\b[xX*•]{2,}\s?\d{3,}\b|\b(?:a/c|acct|account|loan|card)\b[^.\n]{0,25}\b[xX*•]{2,}\s?\d{2,})")
PERSONAL_RE = re.compile(r"\b(your|you|dear customer|aapka|aapke|आपका|आपके|आपकी|ਤੁਹਾਡਾ|ਤੁਹਾਡੇ)\b|आपका|आपके|आपकी|ਤੁਹਾਡ", re.I)
CHANGE_RE = re.compile(
    r"(increas|enhanc|approv|pre-?approved|eligible|credited|debited|withdrawn|limit|offer|disburs|overdue|expire|"
    r"₹|rs\.?\s?\d|inr|बढ़|बढ|मंजूर|ਵਧ|ਮਨਜ਼ੂਰ)", re.I)


def looks_like_notification(text):
    """True for a personalised account alert: masked account/loan number AND 'your' wording AND an amount or change."""
    t = text or ""
    return bool(MASKED_ID_RE.search(t) and PERSONAL_RE.search(t) and CHANGE_RE.search(t))


NOTICE = {
    "kind": "personal_notification",
    "points": [
        "Fact-checks and web sources cannot tell you whether it is genuine.",
        "Check only inside the company's official app or website. Do not click links in the message.",
        "Never share OTPs, PINs, card details or passwords. Real lenders do not ask for them by message.",
        "If in doubt, call the number printed on your card or on the company's official website.",
    ],
}


def check_forward(text=None, image=None, mime=None):
    if text and looks_like_notification(text):
        ext = {"claim": "", "language": "en", "queries": [], "source_text": " ".join(text.split())[:1500]}
        return {"status": "notice", "extraction": ext, "notice": NOTICE}
    ext = extract_claim_from_image(image, mime) if image else extract_claim(text)
    if image and looks_like_notification(ext.get("extracted_text") or ""):
        ext["source_text"] = " ".join((ext.get("extracted_text") or "").split())[:1500]
        return {"status": "notice", "extraction": ext, "notice": NOTICE}
    fix_language(ext, text or "")
    ext["source_text"] = " ".join((text or ext.get("extracted_text") or "").split())[:1500]
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

    # score everything first so weak web-search hits can be dropped
    add_rank_scores(ext["claim"], candidates)

    def keep_related(i, c):
        if verdicts.get(i) not in ("related", "same"):
            return False
        # web-search items have no rating or claim text; show one only if the judge said "same" AND it is close
        if is_web(c):
            return verdicts.get(i) == "same" and c.get("rank_score", 0) >= RELATED_T
        return True

    matches = [c for i, c in enumerate(candidates) if is_match(i, c)]
    related = [c for i, c in enumerate(candidates) if not is_match(i, c) and keep_related(i, c)]
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