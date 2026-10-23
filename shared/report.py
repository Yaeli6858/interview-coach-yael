"""מדפיס את טבלאות ההשוואה ל-REPORT.md מתוך results/api.json ו-results/sdk.json.

python shared/report.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")
HARNESS = ["loop", "tools", "history", "memory", "context", "compaction", "caching", "tokens"]


def main():
    api = json.loads((ROOT / "results" / "api.json").read_text(encoding="utf-8"))
    sdk = json.loads((ROOT / "results" / "sdk.json").read_text(encoding="utf-8"))

    print("| מדד | API | SDK |\n|---|---|---|")
    for label, key in [("input", "input"), ("cache read", "cache_read"),
                       ("cache write", "cache_write"), ("output", "output")]:
        print(f"| טוקנים: {label} | {api['totals']['tokens'][key]:,} | {sdk['totals']['tokens'][key]:,} |")
    print(f"| אחוז cache | {api['totals']['cache_hit_pct']}% | {sdk['totals']['cache_hit_pct']}% |")
    print(f"| קריאות למודל | {api['totals']['model_calls']} | {sdk['totals']['model_calls']} |")
    print(f"| עלות (USD) | ${api['totals']['cost_usd']:.4f} | ${sdk['totals']['cost_usd']:.4f} |")
    print(f"| זמן (שניות) | {api['totals']['seconds']} | {sdk['totals']['seconds']} |")
    print(f"| בדיקות שעברו | {api['checks_passed']} | {sdk['checks_passed']} |")

    print("\n| חלק ב-harness | API (שורות) | SDK (שורות מסומנות replaces) |\n|---|---|---|")
    for name in HARNESS:
        print(f"| {name} | {api['lines_of_code'].get(name, 0)} | {sdk['lines_of_code'].get(name, 0)} |")
    print(f"| **סה\"כ** | {api['lines_of_code'].get('total_harness', 0)} | "
          f"{sdk['lines_of_code'].get('total_sdk_code', 0)} (כל קוד ה-SDK) |")

    print("\n| תור | API: in / cache read / out | SDK: in / cache read / out | כלים API | כלים SDK |\n|---|---|---|---|---|")
    for a, s in zip(api["turns"], sdk["turns"]):
        ta, ts = a["tokens"], s["tokens"]
        print(f"| {a['turn']} | {ta['input']} / {ta['cache_read']} / {ta['output']} | "
              f"{ts['input']} / {ts['cache_read']} / {ts['output']} | {', '.join(a['tools'])} | {', '.join(s['tools'])} |")


if __name__ == "__main__":
    main()
