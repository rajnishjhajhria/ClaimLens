import csv
from collections import defaultdict
from pathlib import Path

SAME_T = 0.87      # edit these after reading the sweep
RELATED_T = 0.82

path = Path(__file__).parent / "eval" / "labeled.csv"
rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
rows = [r for r in rows if r["label"].strip()]
for r in rows:
    r["score"] = float(r["score"])
    r["label"] = r["label"].strip().upper()


def prf(rs, t, positives):
    tp = sum(1 for r in rs if r["score"] >= t and r["label"] in positives)
    fp = sum(1 for r in rs if r["score"] >= t and r["label"] not in positives)
    fn = sum(1 for r in rs if r["score"] < t and r["label"] in positives)
    p = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return p, rec


counts = defaultdict(int)
for r in rows:
    counts[r["label"]] += 1
print("Labeled rows:", dict(counts), "\n")

print("SAME vs everything else (S is positive)")
print("threshold  precision  recall")
for t in [x / 100 for x in range(80, 96)]:
    p, rec = prf(rows, t, {"S"})
    print(f"  {t:.2f}      {p:.2f}       {rec:.2f}")

print("\nRELEVANT vs UNRELATED (S or R is positive)")
print("threshold  precision  recall")
for t in [x / 100 for x in range(74, 90)]:
    p, rec = prf(rows, t, {"S", "R"})
    print(f"  {t:.2f}      {p:.2f}       {rec:.2f}")

print(f"\nPer language at SAME_T={SAME_T}")
by_lang = defaultdict(list)
for r in rows:
    by_lang[r["lang"]].append(r)
for lang, rs in by_lang.items():
    p, rec = prf(rs, SAME_T, {"S"})
    n_same = sum(1 for r in rs if r["label"] == "S")
    print(f"  {lang:9} rows={len(rs):3}  same-labeled={n_same:2}  precision={p:.2f}  recall={rec:.2f}")

print("\nRanking quality (per claim, ignoring random negatives)")
by_claim = defaultdict(list)
for r in rows:
    if r.get("draft_note") != "random negative":
        by_claim[r["id"]].append(r)
hit1 = hit3 = n = 0
rr = 0.0
for cid, rs in by_claim.items():
    if not any(r["label"] == "S" for r in rs):
        continue
    n += 1
    ranked = sorted(rs, key=lambda r: -r["score"])
    first = next(i for i, r in enumerate(ranked) if r["label"] == "S")
    hit1 += first == 0
    hit3 += first < 3
    rr += 1 / (first + 1)
print(f"  claims with at least one S: {n}")
print(f"  top-1 is S: {hit1}/{n}   S within top-3: {hit3}/{n}   MRR: {rr / n:.2f}")