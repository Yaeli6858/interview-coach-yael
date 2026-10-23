"""הרצת התרחיש על גרסת ה-SDK.

python SDK/main.py --scenario scenario.json --out results/sdk.json
רץ על ה-login שלך ב-Claude Code. ANTHROPIC_API_KEY חייב להיות לא מוגדר.
"""
import argparse
import asyncio
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from shared.scenario import count_code_lines, run_scenario  # noqa: E402
from shared.store import Store  # noqa: E402

MODEL = "claude-opus-5-5"
EFFORT = "medium"
SDK_FILES = ["agent.py", "tools.py", "main.py"]


def count_replaced_lines():
    """סופר שורות שמסומנות '# replaces: X' לכל קובץ X של ה-harness."""
    counts = Counter()
    for name in ["agent.py", "tools.py"]:
        for line in (ROOT / "SDK" / name).read_text(encoding="utf-8").splitlines():
            m = re.search(r"#\s*replaces:\s*(.+)$", line)
            if m:
                for target in m.group(1).split(","):
                    counts[target.strip().removesuffix(".py")] += 1
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="scenario.json")
    parser.add_argument("--out", default="results/sdk.json")
    parser.add_argument("--state", default=str(ROOT / "state" / "sdk"))
    args = parser.parse_args()

    if os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY מוגדר, והחיוב יעבור למפתח. בטלי אותו:  Remove-Item Env:ANTHROPIC_API_KEY")

    import claude_agent_sdk
    from SDK.agent import Agent

    store = Store(args.state)

    async def make_agent(session_index):
        return await Agent.create(store, MODEL, EFFORT)  # סשן חדש, בלי resume: רק הזיכרון מהדיסק

    replaced = count_replaced_lines()
    harness = ["loop", "tools", "history", "memory", "context", "compaction", "caching", "tokens"]
    lines = {name: replaced.get(name, 0) for name in harness}
    lines["total_sdk_code"] = sum(count_code_lines(ROOT / "SDK" / f) for f in SDK_FILES)

    meta = {"model": MODEL, "effort": EFFORT, "library": f"claude-agent-sdk {claude_agent_sdk.__version__}"}
    asyncio.run(run_scenario(args.scenario, args.out, "SDK", make_agent, store, lines, meta))


if __name__ == "__main__":
    main()
