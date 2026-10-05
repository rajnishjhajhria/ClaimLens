"""Held-out evaluation. Run it ONCE, after the judge prompt, labeling rule and
thresholds are frozen.

Reads (backend/eval/):
  claims_test.json       the test claims (+ claims_test_extra.json if present)
  test_candidates.json   written by collect_pairs_test.py (has the embedding scores)
  labeled_test.csv       your labels: S / F / R / U

Labels
  S  same rumor, even through a different instance (video, person, party, date, amount)
  F  sibling rumor in the same family (a different remedy, or a company running the same scam)
  R  same topic only
  U  unrelated

"strict" counts only S as a correct match; "family" counts S and F.
"""
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from pipeline import JUDGE_PROMPT, judge
from reranker import SAME_T, RELATED_T, score_candidates

EVAL = Path(__file__).parent / "eval"
MAP = {"same": "S", "related": "R", "unrelated": "U"}
VALID = {"S", "F", "R", "U"}
SAME_TOPIC_GROUPS = [
    {105, 109, 111, 119},  # different rumors of the same genre (phishing scams)
    {108, 120},            # different cancer rumors
]
N_NEG = 3
NAN = float("nan")


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

print("FROZEN SETTINGS (write these down before you look at any results)")
print("  judge prompt fingerprint:", hashlib.sha256(JUDGE_PROMPT.encode()).hexdigest()[:12])
print(f"  SAME_THRESHOLD={SAME_T}  RELATED_THRESHOLD={RELATED_T}\n")

# ---------- load ----------
claims = {c["id"]: c for c in load_claims()}
cands = json.loads((EVAL / "test_candidates.json").read_text(encoding="utf-8"))

labels = {}
with open(EVAL / "labeled_test.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        labels[(int(r["id"]), r["url"])] = (r.get("label") or "").strip().upper()

bad = [(c["id"], c["url"]) for c in cands if labels.get((c["id"], c["url"])) not in VALID]
if bad:
    print(f"{len(bad)} rows are missing a valid label (S/F/R/U) in labeled_test.csv, for example:")
    for b in bad[:5]:
        print("  ", b)
    raise SystemExit(1)

rows = [{
    "id": c["id"], "lang": c["lang"], "claim": c["claim"], "title": c["title"],
    "fc": c["fact_checked_claim"], "url": c["url"], "score": c["score"],
    "label": labels[(c["id"], c["url"])], "neg": False,
} for c in cands]

by_id = defaultdict(list)
for r in rows:
    by_id[r["id"]].append(r)


def same_group(a, b):
    return any(a in g and b in g for g in SAME_TOPIC_GROUPS)


# ---------- random negatives (fact-checks borrowed from other claims) ----------
rng = random.Random(0)
negs = []
for cid, rs in by_id.items():
    pool = [r for oid, o in by_id.items()
            if oid != cid and not same_group(cid, oid) for r in o]
    picks = rng.sample(pool, min(N_NEG, len(pool)))
    sc = score_candidates(rs[0]["claim"], [{"title": p["title"], "claim": p["fc"]} for p in picks])
    for p, s in zip(picks, sc):
        negs.append({**p, "id": cid, "lang": rs[0]["lang"], "claim": rs[0]["claim"],
                     "score": round(s, 3), "label": "U", "neg": True})

all_rows = rows + negs
by_claim = defaultdict(list)
for r in all_rows:
    by_claim[r["id"]].append(r)

# ---------- LLM judge (one call per claim; results are cached) ----------
failed = []
for cid in sorted(by_claim):
    rs = by_claim[cid]
    cs = [{"title": r["title"], "claim": r["fc"]} for r in rs]
    try:
        verdicts = judge(rs[0]["claim"], cs)
    except Exception as e:
        failed.append(cid)
        print(f"claim {cid}: LLM failed ({str(e)[:90]})")
        continue
    for i, r in enumerate(rs):
        r["llm"] = MAP.get(verdicts.get(i), "?")
    print(f"claim {cid} judged")

if failed:
    print(f"\nIncomplete: claims {failed} were not judged. Finished claims are cached,")
    print("so run this script again later (no results are shown until all claims are done).")
    raise SystemExit(1)


# ---------- metrics ----------
def prf(rs, pred, pos):
    tp = sum(1 for r in rs if pred(r) and r["label"] in pos)
    fp = sum(1 for r in rs if pred(r) and r["label"] not in pos)
    fn = sum(1 for r in rs if not pred(r) and r["label"] in pos)
    p = tp / (tp + fp) if tp + fp else NAN
    rec = tp / (tp + fn) if tp + fn else NAN
    return p, rec


def fmt(x):
    return "n/a" if x != x else f"{x:.2f}"


def boot(groups, pred, pos, n=2000, seed=0):
    """95% interval from resampling whole claims."""
    rg = random.Random(seed)
    ids = list(groups)
    ps, rcs = [], []
    for _ in range(n):
        sample = [r for cid in (rg.choice(ids) for _ in ids) for r in groups[cid]]
        p, rec = prf(sample, pred, pos)
        if p == p:
            ps.append(p)
        if rec == rec:
            rcs.append(rec)

    def ci(v):
        if not v:
            return NAN, NAN
        v.sort()
        return v[int(0.025 * len(v))], v[min(len(v) - 1, int(0.975 * len(v)))]

    return ci(ps), ci(rcs)


METHODS = [
    ("LLM judge", lambda r: r["llm"] == "S"),
    (f"embedding >= {SAME_T}", lambda r: r["score"] >= SAME_T),
    ("always 'same' (baseline)", lambda r: True),
]
DEFS = [("STRICT (only S is correct)", {"S"}), ("FAMILY (S and F are correct)", {"S", "F"})]

n_claims = len(by_claim)
print(f"\nrows: {len(rows)} real candidates + {len(negs)} random negatives, across {n_claims} claims")
print("label counts (real candidates):", dict(Counter(r["label"] for r in rows)))
on_topic = rows
print(f"baseline on the on-topic pool (no random negatives): "
      f"S share = {sum(r['label'] == 'S' for r in on_topic) / len(on_topic):.2f}, "
      f"S+F share = {sum(r['label'] in ('S', 'F') for r in on_topic) / len(on_topic):.2f}")

for dname, pos in DEFS:
    print(f"\n{dname}   [95% interval from resampling claims]")
    for mname, fn in METHODS:
        p, rec = prf(all_rows, fn, pos)
        (pl, ph), (rl, rh) = boot(by_claim, fn, pos)
        print(f"  {mname:26} precision {fmt(p)} [{fmt(pl)}-{fmt(ph)}]   recall {fmt(rec)} [{fmt(rl)}-{fmt(rh)}]")

print("\nLLM judge confusion (true label -> predicted):")
conf = Counter((r["label"], r["llm"]) for r in all_rows)
for t in "SFRU":
    print(f"  true {t}: " + "  ".join(f"{p}={conf[(t, p)]}" for p in "SRU?"))

print("\nPER LANGUAGE (language of the forward)")
by_lang = defaultdict(list)
for r in all_rows:
    by_lang[r["lang"]].append(r)
for lang, rs in sorted(by_lang.items()):
    n_cl = len({r["id"] for r in rs})
    line = f"  {lang:9} claims={n_cl} rows={len(rs):3} "
    for tag, pos in (("strict", {"S"}), ("family", {"S", "F"})):
        for mname, fn in METHODS[:2]:
            p, rec = prf(rs, fn, pos)
            short = "LLM" if mname == "LLM judge" else "emb"
            line += f"| {tag} {short} P={fmt(p)} R={fmt(rec)} "
    print(line)

print("\nRANKING BY EMBEDDING SCORE (real candidates only)")
for dname, pos in (("strict", {"S"}), ("family", {"S", "F"})):
    n = hit1 = hit3 = 0
    rr = 0.0
    for cid, rs in by_id.items():
        ranked = sorted(rs, key=lambda r: -r["score"])
        idx = [i for i, r in enumerate(ranked) if r["label"] in pos]
        if not idx:
            continue
        n += 1
        hit1 += idx[0] == 0
        hit3 += idx[0] < 3
        rr += 1 / (idx[0] + 1)
    if n:
        print(f"  {dname}: claims with a correct match={n}  top-1={hit1}/{n}  top-3={hit3}/{n}  MRR={rr / n:.2f}")

print("\nSEARCH COVERAGE (Fact Check API only)")
print("  id  lang      expected  candidates  S  F  R")
for cid in sorted(claims):
    rs = by_id.get(cid, [])
    cnt = Counter(r["label"] for r in rs)
    print(f"  {cid}  {claims[cid]['lang']:9} {claims[cid].get('expect_covered', '?'):8}  "
          f"{len(rs):10}  {cnt['S']}  {cnt['F']}  {cnt['R']}")
yes_ids = [c for c, v in claims.items() if v.get("expect_covered") == "yes"]
print(f"  claims expected covered that have at least one S: "
      f"{sum(1 for c in yes_ids if any(r['label'] == 'S' for r in by_id.get(c, [])))} of {len(yes_ids)}")


# ---------- error analysis (after the fact: for the write-up, NOT for tuning) ----------
prov = {}
with open(EVAL / "labeled_test.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        prov[(int(r["id"]), r["url"])] = (r.get("labeled_by") or "you").strip() or "you"

print("\nERROR ANALYSIS: rows where the LLM verdict differs from the label (real candidates)")
n_diff = 0
for r in sorted(rows, key=lambda r: (r["id"], -r["score"])):
    if r["llm"] != r["label"]:
        n_diff += 1
        print(f"  claim {r['id']} | label={r['label']} llm={r['llm']} | score={r['score']:.3f} "
              f"| by={prov[(r['id'], r['url'])][:9]} | {r['title'][:70]}")
print(f"  {n_diff} rows")

print("\nBY WHO LABELED THE ROW (real candidates only, LLM judge, strict)")
for who in sorted(set(prov.values())):
    sub = [r for r in rows if prov[(r["id"], r["url"])] == who]
    p, rec = prf(sub, lambda r: r["llm"] == "S", {"S"})
    print(f"  {who:24} rows={len(sub):3}  precision={fmt(p)}  recall={fmt(rec)}")