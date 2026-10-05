"""Run one AI check from the terminal, no server needed.  Usage:  python try_ai_check.py "India won the T20 World Cup in 2024"
Prints the verdict, summary, sources and whether Google's search suggestions came back."""
import json
import sys

from ai_check import AiCheckError, ai_check

claim = " ".join(sys.argv[1:]) or "India won the T20 World Cup in 2024"
try:
    r = ai_check(claim)
except AiCheckError as e:
    sys.exit(f"{e.kind.upper()}: {e.message}")
print("VERDICT :", r["verdict"], "| grounded:", r["grounded"], "| model:", r["model"], "| cached:", r["cached"])
print("SUMMARY :", r["summary"])
for s in r["sources"]:
    print(f"  [{s['n']}] {s['title']}  {s['url'][:90]}")
print("QUERIES :", r["queries"])
print("SEARCH SUGGESTIONS HTML:", "yes" if r["search_suggestions_html"] else "NO (tell me, the UI relies on it)")
