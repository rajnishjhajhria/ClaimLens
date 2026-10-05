"""Run every screenshot in a folder through the pipeline and write a results table.

Usage (from backend\\):   python test_screenshots.py screenshots
Name each file with a prefix so the script can auto-check it:
    en_  hi_  pa_  hinglish_   = the language of the message (e.g. hi_atm_notes.png)
    none_                      = a screenshot with NO checkable claim (e.g. none_normal_chat.png)
Output: screenshot_results.csv (open in Excel; fill the last two columns by reading each row).

Quota note: each image uses about 2 Gemini calls (read + judge). On the free tier (20 per model per day)
run about 8 images per day, or set GEMINI_FALLBACK_MODEL in .env. Results are cached, so re-runs are free.
"""
import csv
import mimetypes
import sys
import time
from pathlib import Path

from pipeline import check_forward

folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "screenshots"
files = sorted(p for p in folder.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
if not files:
    sys.exit(f"No images found in {folder.resolve()}")

LANGS = {"en", "hi", "pa", "hinglish"}
rows = []
for p in files:
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    prefix = p.stem.split("_")[0].lower()
    try:
        r = check_forward(image=p.read_bytes(), mime=mime)
    except RuntimeError as e:
        print(f"STOPPED at {p.name}: {e}\nThe daily limit is probably used up. Re-run tomorrow; finished images are cached.")
        break
    ex = r.get("extraction") or {}
    status, lang = r.get("status"), ex.get("language")
    auto = ""
    if prefix == "none":
        auto = "OK" if status == "no_claim" else "CHECK: expected no_claim"
    elif prefix in LANGS:
        auto = "OK" if lang == prefix else f"CHECK: language {lang} vs expected {prefix}"
    top = (r.get("matches") or r.get("unjudged") or r.get("related") or [{}])[0]
    row = {
        "file": p.name,
        "auto_check": auto,
        "status": status,
        "language": lang,
        "claim": ex.get("claim"),
        "text_read": " ".join((ex.get("extracted_text") or "").split())[:300],
        "matches": len(r.get("matches") or []),
        "top_result": f"{top.get('publisher', '')} | {top.get('rating', '')} | {top.get('title', '')}"[:200] if top else "",
        "text_read_correctly (y/n)": "",
        "claim_correct (y/n)": "",
    }
    rows.append(row)
    print(f"{p.name:35} {status:10} lang={lang!s:9} {auto or '-':28} claim: {str(row['claim'])[:70]}")
    time.sleep(2)

if rows:
    out = Path("screenshot_results.csv")
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {out.resolve()}  ({len(rows)} images). Open it, read each row against its image, fill the last two columns.")