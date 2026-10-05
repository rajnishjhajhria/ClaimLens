import csv
import json
from pathlib import Path

from factcheck_api import search_claims
from reranker import score_candidates

EVAL = Path(__file__).parent / "eval"
TOP_K = 6


def main():
    items = json.loads((EVAL / "claims.json").read_text(encoding="utf-8"))
    rows = []
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
            rows.append({
                "id": it["id"], "lang": it["lang"], "claim": it["claim"],
                "title": c["title"], "fact_checked_claim": c["claim"],
                "url": c["url"], "score": round(s, 3), "label": "",
            })

    out = EVAL / "to_label.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()