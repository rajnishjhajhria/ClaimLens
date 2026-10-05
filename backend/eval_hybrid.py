import csv
from collections import defaultdict
from pathlib import Path

from pipeline import judge

LOW, HIGH = 0.83, 0.90
MAP = {"same": "S", "related": "R", "unrelated": "U"}

path = Path(__file__).parent / "eval" / "labeled.csv"
rows = [r for r in csv.DictReader(open(path, encoding="utf-8-sig")) if r["label"].strip()]
for r in rows:
    r["score"] = float(r["score"])
    r["label"] = r["label"].strip().upper()
    r["llm"] = "?"

by_claim = defaultdict(list)
for r in rows:
    by_claim[r["id"]].append(r)

# same prompts as eval_llm_judge.py, so these calls should come from the cache
for cid, rs in by_claim.items():
    cands = [{"title": r["title"], "claim": r["fact_checked_claim"]} for r in rs]
    try:
        verdicts = judge(rs[0]["claim"], cands)
    except Exception as e:
        print(f"claim {cid}: LLM failed ({e})")
        continue
    for i, r in enumerate(rs):
        r["llm"] = MAP.get(verdicts.get(i), "?")


def hybrid(r):
    if r["score"] >= HIGH:
        return "S"
    if r["score"] < LOW:
        return "U"
    return r["llm"]


def prf(pairs):
    tp = sum(1 for t, p in pairs if t == "S" and p == "S")
    fp = sum(1 for t, p in pairs if t != "S" and p == "S")
    fn = sum(1 for t, p in pairs if t == "S" and p != "S")
    return (tp / (tp + fp) if tp + fp else 0.0), (tp / (tp + fn) if tp + fn else 0.0)


methods = {
    "embedding >= 0.90": lambda r: "S" if r["score"] >= 0.90 else "R",
    "LLM judge only": lambda r: r["llm"],
    f"hybrid ({LOW}/{HIGH})": hybrid,
}
print("method                  precision  recall")
for name, fn in methods.items():
    p, rec = prf([(r["label"], fn(r)) for r in rows])
    print(f"{name:22}   {p:.2f}      {rec:.2f}")

needs_llm = sum(
    1 for rs in by_claim.values() if any(LOW <= r["score"] < HIGH for r in rs)
)
print(f"\nclaims where the hybrid still needs the LLM: {needs_llm} of {len(by_claim)}")

print("\nLLM vs your label, rows that disagree:")
for r in rows:
    if r["llm"] != r["label"]:
        print(f"  claim {r['id']:>2} | you={r['label']} llm={r['llm']} | score={r['score']:.3f}"
              f" | {r['title'][:65]} | {r.get('draft_note', '')[:50]}")