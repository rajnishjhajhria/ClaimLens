"""Checks the personal-notification rule: it must fire on account alerts and on none of the known rumours."""
import glob
import json
import re
import sys
from pathlib import Path

# the rule is plain regex, so stub the modules that need Gemini / the embedding model
for mod, names in {
    "claim_extractor": ("extract_claim", "extract_claim_from_image", "llm_json"),
    "factcheck_api": ("search_claims",),
    "reranker": ("judge_embedding",),
    "rank": ("add_rank_scores", "sort_key"),
}.items():
    m = type(sys)(mod)
    for n in names:
        setattr(m, n, lambda *a, **k: None)
    if mod == "reranker":
        m.RELATED_T = 0.82
    sys.modules[mod] = m
from pipeline import looks_like_notification  # noqa: E402

POSITIVE = [
    "Dear customer, your loan amount on account xxx8898 has increased to Rs. 2,50,000. Click link to avail. Navi Finserv RBI registered NBFC",
    "Your pre-approved loan of ₹1,50,000 on A/c XXXX4521 is ready. Apply now",
    "आपका लोन खाता xxx8898 पर राशि बढ़ गई है, ₹50,000 पाएं",
]
NEGATIVE = [
    "Bhai ye forward kar do, kal se sabhi ATM se 500 ke note band ho jayenge, RBI ne order nikala hai",
    "मोदी सरकार सभी को फ्री मोबाइल रिचार्ज दे रही है, इस लिंक पर क्लिक करके पाएं",
    "Drinking hot water with lemon every morning cures cancer, doctors are hiding this!",
    "Navi Finserv is an RBI registered NBFC",
    "Your account will be blocked, send your OTP",  # no masked id: left to the normal pipeline
]
eval_dir = Path(__file__).parent / "eval"
for f in glob.glob(str(eval_dir / "*.json")):
    try:
        data = json.loads(Path(f).read_text(encoding="utf-8"))
    except Exception:
        continue
    if isinstance(data, list):
        NEGATIVE += [d["claim"] for d in data if isinstance(d, dict) and isinstance(d.get("claim"), str)]

bad = 0
for t in POSITIVE:
    ok = looks_like_notification(t)
    bad += not ok
    print("OK  " if ok else "MISS", "positive:", t[:70])
fp = [t for t in NEGATIVE if looks_like_notification(t)]
print(f"\n{len(NEGATIVE)} known rumours/claims checked, false positives: {len(fp)}")
for t in fp:
    print("  FALSE POSITIVE:", t[:90])
sys.exit(1 if bad or fp else 0)
