"""Collect candidate fact-checks for the held-out test claims.

Reads  : eval/claims_test.json (+ eval/claims_test_extra.json if present)
Writes : eval/to_label_test.csv     (what you label; NO scores, shuffled)
         eval/test_candidates.json  (same rows plus the embedding scores; used by evaluate_test.py)

It never touches the development files (claims.json, labeled.csv, ...).
"""
import csv
import json
import random
from pathlib import Path

from factcheck_api import search_claims
from reranker import score_candidates

EVAL = Path(__file__).parent / "eval"
TOP_K = 6  # same as the development set


def load_claims():
    """claims_test.json plus claims_test_extra.json (if present)."""
    items = []
    for name in ("claims_test.json", "claims_test_extra.json"):
        p = EVAL / name
        if p.exists():
            items += json.loads(p.read_text(encoding="utf-8"))
    ids = [c["id"] for c in items]
    assert len(ids) == len(set(ids)), "duplicate claim ids"
    return items


def main():
    items = load_claims()
    store = []

    for it in items:
        seen = {}
        for q, lang in it["queries"]:
            try:
                for r in search_claims(q, lang):
                    if r["url"] and r["url"] not in seen:
                        seen[r["url"]] = r
            except Exception as e:
                print("  search failed:", q, e)
        cands = list(seen.values())
        print(f"claim {it['id']} ({it['lang']}): {len(cands)} candidates")
        if not cands:
            continue
        scores = score_candidates(it["claim"], cands)
        ranked = sorted(zip(cands, scores), key=lambda x: -x[1])[:TOP_K]
        for c, s in ranked:
            store.append({
                "id": it["id"], "lang": it["lang"], "claim": it["claim"],
                "title": c["title"] or "", "fact_checked_claim": c["claim"] or "",
                "url": c["url"], "score": round(s, 3),
            })

    if not store:
        raise SystemExit("no candidates found for any claim")

    (EVAL / "test_candidates.json").write_text(
        json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")

    # Blind labeling sheet: no score column, rows shuffled so rank doesn't leak
    sheet = [{k: r[k] for k in ("id", "lang", "claim", "title", "fact_checked_claim", "url")}
             | {"label": ""} for r in store]
    random.Random(0).shuffle(sheet)
    sheet.sort(key=lambda r: r["id"])           # group by claim ...
    by_claim = {}
    for r in sheet:
        by_claim.setdefault(r["id"], []).append(r)
    final = []
    for cid, rs in by_claim.items():             # ... but shuffle inside each claim
        random.Random(cid).shuffle(rs)
        final.extend(rs)

    out = EVAL / "to_label_test.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(final[0].keys()))
        w.writeheader()
        w.writerows(final)
    print(f"wrote {len(final)} rows to {out.name} and test_candidates.json")


if __name__ == "__main__":
    main()