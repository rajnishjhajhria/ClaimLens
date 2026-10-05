"""Carry your existing labels into the regenerated labeling sheet.

Run this AFTER collect_pairs_test.py has been re-run with the extra claims.

  reads : eval/to_label_test.csv     (fresh sheet from collect_pairs_test.py)
          eval/labeled_test.csv      (your labels so far)
  writes: eval/labeled_test.csv      (fresh sheet with your old labels filled in; new rows blank)
  backup: eval/labeled_test_backup.csv  (your original file, made once)

Safe to run again: labels already typed into labeled_test.csv are kept.
"""
import csv
import shutil
from collections import Counter
from pathlib import Path

EVAL = Path(__file__).parent / "eval"
sheet_path = EVAL / "to_label_test.csv"
labeled = EVAL / "labeled_test.csv"
backup = EVAL / "labeled_test_backup.csv"


def read(p):
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


if labeled.exists() and not backup.exists():
    shutil.copy(labeled, backup)

known = {}
for p in (backup, labeled):  # labeled_test.csv last, so newer labels win
    if p.exists():
        for r in read(p):
            lab = (r.get("label") or "").strip().upper()
            if lab:
                known[(int(r["id"]), r["url"])] = lab

sheet = read(sheet_path)
fields = list(sheet[0].keys())
present = set()
carried = 0
for r in sheet:
    key = (int(r["id"]), r["url"])
    present.add(key)
    r["label"] = known.get(key, "")
    carried += key in known

dropped = [k for k in known if k not in present]

with open(labeled, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(sheet)

blank = Counter(int(r["id"]) for r in sheet if not r["label"])
print(f"rows in new sheet: {len(sheet)}")
print(f"labels carried over: {carried}")
print(f"rows still to label: {sum(blank.values())}")
if blank:
    print("  per claim:", dict(sorted(blank.items())))
if dropped:
    print(f"old labels with no matching row in the new sheet (search results changed): {len(dropped)}")
    for k in dropped[:5]:
        print("  ", k)
