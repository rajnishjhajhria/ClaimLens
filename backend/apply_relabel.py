"""Apply the v2 labeling rule to eval/labeled.csv.

Rule v2
  S: debunks the same rumor the forward spreads, even through a different
     instance (video, person, political party, date, amount, threshold).
  R: same topic, but a different rumor (different remedy or mechanism,
     or a company instead of a political actor).
  U: different topic.

Safe to run more than once: it always starts from labeled_v1.csv.
"""
import csv
import shutil
from pathlib import Path

EVAL = Path(__file__).parent / "eval"
path = EVAL / "labeled.csv"
backup = EVAL / "labeled_v1.csv"
if not backup.exists():
    shutil.copy(path, backup)

CHANGES = {
    (2, 'https://fullfact.org/online/coronavirus-5G/'): ('S', 'borderline: headline debunks 5G/coronavirus claims; the listed claim is a side claim about tower counts'),
    (2, 'https://apnews.com/article/archive-fact-checking-8970130129'): ('S', 'borderline: a specific viral video (instance) of the 5G-coronavirus rumor'),
    (2, 'https://fullfact.org/health/eg5-covid-not-connected-5g/'): ('S', "borderline: EG.5 variant 'is a 5G virus', an instance of the same rumor"),
    (2, 'https://fullfact.org/online/5g-tower-with-delta-power-system-is-not-related-to-covid-19/'): ('S', "borderline: one specific 5G tower photo used as 'proof' of the same rumor"),
    (5, 'https://www.telugupost.com/english-factcheck/viral-message-claiming-bjp-is-providing-three-months-of-free-recharge-to-all-indian-mobile-service-customers-is-hoax-1501939'): ('S', 'borderline: BJP (political party) giving 3 months free recharge; same hoax as the Modi version'),
    (7, 'https://apnews.com/article/archive-fact-checking-8736262219'): ('S', 'borderline: headline says drinking hot water with lemon will not cure coronavirus; listed claim is about Israel'),
    (9, 'https://www.vishvasnews.com/society/fact-check-viral-message-regarding-counterfeit-note-of-500-rs-note-is-fake/'): ('R', 'same topic (Rs 500 notes) but a different rumor (spotting counterfeit notes)'),
    (12, 'https://www.factcheck.org/2021/07/scicheck-spoof-video-furthers-microchip-conspiracy-theory/'): ('S', "borderline: spoof video 'proving' a chip in a vaccinated arm; instance of the same rumor"),
    (12, 'https://factcheck.afp.com/doc.afp.com.9EG2NX'): ('S', 'borderline: video of a chip in the Pfizer vaccine; instance of the same rumor'),
    (13, 'https://www.vishvasnews.com/punjabi/viral/fact-check-the-link-going-viral-on-social-media-with-the-claim-of-congress-free-recharge-scheme-is-fake/'): ('S', 'borderline: Congress (political party) free recharge link; same hoax family as the government version'),
    (13, 'https://www.vishvasnews.com/punjabi/viral/fact-check-claim-of-free-recharge-by-congress-in-exchange-for-votes-in-2024-elections-is-fake/'): ('S', 'borderline: Rahul Gandhi/Congress free recharge for 2024 elections; same hoax family'),
}

rows = list(csv.DictReader(open(backup, encoding="utf-8-sig")))
fields = list(rows[0].keys())
if "label_v1" not in fields:
    fields.append("label_v1")
if "draft_note" not in fields:
    fields.append("draft_note")

applied = set()
for r in rows:
    r["label_v1"] = r["label"]
    key = (int(r["id"]), r["url"])
    if key in CHANGES:
        r["label"], r["draft_note"] = CHANGES[key]
        applied.add(key)

missing = set(CHANGES) - applied
assert not missing, f"rows not found in labeled.csv: {missing}"

with open(path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

changed = sum(1 for r in rows if r["label"] != r["label_v1"])
print(f"updated {changed} labels; backup of the old file is {backup.name}")
