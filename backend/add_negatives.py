import csv
import random
from pathlib import Path
from reranker import score_candidates

random.seed(0)
path = Path(__file__).parent / "eval" / "labeled.csv"
rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
fields = list(rows[0].keys())

by_id = {}
for r in rows:
    by_id.setdefault(r["id"], []).append(r)

# claim pairs that share a topic, so they can't serve as negatives for each other
SAME_TOPIC = {("5", "13"), ("13", "5"), ("1", "7"), ("7", "1")}

new = []
for cid, rs in by_id.items():
    others = [r for oid, o in by_id.items()
              if oid != cid and (cid, oid) not in SAME_TOPIC for r in o]
    picks = random.sample(others, 3)
    cands = [{"title": p["title"], "claim": p["fact_checked_claim"]} for p in picks]
    scores = score_candidates(rs[0]["claim"], cands)
    for p, s in zip(picks, scores):
        new.append({**p, "id": cid, "lang": rs[0]["lang"], "claim": rs[0]["claim"],
                    "score": round(s, 3), "label": "U", "draft_note": "random negative"})

with open(path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows + new)
print(f"added {len(new)} random negatives")