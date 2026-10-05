import csv
from collections import defaultdict, Counter
from pathlib import Path

from pipeline import judge

path = Path(__file__).parent / "eval" / "labeled.csv"
rows = [r for r in csv.DictReader(open(path, encoding="utf-8-sig")) if r["label"].strip()]

by_claim = defaultdict(list)
for r in rows:
    by_claim[r["id"]].append(r)

MAP = {"same": "S", "related": "R", "unrelated": "U"}
results = []  # (row, true_label, predicted)

for cid, rs in by_claim.items():
    cands = [{"title": r["title"], "claim": r["fact_checked_claim"]} for r in rs]
    try:
        verdicts = judge(rs[0]["claim"], cands)
    except Exception as e:
        print(f"claim {cid}: LLM failed ({e}); rerun later, finished claims are cached")
        continue
    for i, r in enumerate(rs):
        results.append((r, r["label"].strip().upper(), MAP.get(verdicts.get(i), "?")))
    print(f"claim {cid} done")


def prf(rs):
    tp = sum(1 for _, t, p in rs if t == "S" and p == "S")
    fp = sum(1 for _, t, p in rs if t != "S" and p == "S")
    fn = sum(1 for _, t, p in rs if t == "S" and p != "S")
    return (tp / (tp + fp) if tp + fp else 0.0), (tp / (tp + fn) if tp + fn else 0.0)


print("\nConfusion (true -> predicted):")
conf = Counter((t, p) for _, t, p in results)
for t in "SRU":
    print(f"  true {t}: " + "  ".join(f"{p}={conf[(t, p)]}" for p in "SRU?"))

p, rec = prf(results)
print(f"\nLLM judge, SAME vs rest: precision={p:.2f} recall={rec:.2f}")

by_lang = defaultdict(list)
for item in results:
    by_lang[item[0]["lang"]].append(item)
for lang, rs in by_lang.items():
    p, rec = prf(rs)
    print(f"  {lang:9} rows={len(rs):3}  precision={p:.2f}  recall={rec:.2f}")