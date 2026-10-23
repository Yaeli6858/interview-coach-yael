"""הרצת התרחיש על גרסת ה-API.

python API/main.py --scenario scenario.json --out results/api.json
דורש ANTHROPIC_API_KEY כמשתנה סביבה (לעולם לא בקוד).
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")  # עברית תקינה גם ב-PowerShell

from shared.scenario import count_code_lines, run_scenario  # noqa: E402
from shared.store import Store  # noqa: E402

MODEL = "claude-opus-5-5"
EFFORT = "medium"
HARNESS_FILES = ["loop", "tools", "history", "memory", "context", "compaction", "caching", "tokens"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="scenario.json")
    parser.add_argument("--out", default="results/api.json")
    parser.add_argument("--state", default=str(ROOT / "state" / "api"))
    parser.add_argument("--compaction-threshold", type=int, default=20000)
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("חסר ANTHROPIC_API_KEY. הגדירי אותו בטרמינל:  $env:ANTHROPIC_API_KEY = \"sk-ant-...\"")

    import anthropic
    from API.agent import Agent

    client = anthropic.Anthropic()
    store = Store(args.state)

    def make_agent(session_index):
        return Agent(client, store, f"session{session_index}", MODEL, EFFORT,
                     compaction_threshold=args.compaction_threshold)

    harness_dir = ROOT / "API" / "harness"
    lines = {name: count_code_lines(harness_dir / f"{name}.py") for name in HARNESS_FILES}
    lines["agent.py + main.py"] = count_code_lines(ROOT / "API" / "agent.py") + count_code_lines(ROOT / "API" / "main.py")
    lines["total_harness"] = sum(lines[n] for n in HARNESS_FILES)

    meta = {"model": MODEL, "effort": EFFORT, "library": f"anthropic {anthropic.__version__}"}
    asyncio.run(run_scenario(args.scenario, args.out, "API", make_agent, store, lines, meta))


if __name__ == "__main__":
    main()
