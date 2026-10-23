"""מריץ את כל התרחיש על גרסת ה-API עם client מדומה, ובודק שהבדיקות על המצב עוברות.

כך אפשר לוודא שה-runner, השמירה לדיסק והבדיקות עובדים, לפני שמשלמים על ריצה אמיתית.
"""
import asyncio
import json
from pathlib import Path

from fakes import FakeClient, response, text, tool_use

from API.agent import Agent
from shared.scenario import run_scenario

ROOT = Path(__file__).resolve().parent.parent


def scripted_responses():
    def step(tools, final):
        out = []
        if tools:
            out.append(response([tool_use(f"t{i}", n, a) for i, (n, a) in enumerate(tools)], "tool_use"))
        out.append(response([text(final)], "end_turn"))
        return out

    return (
        step([("read_job_description", {"filename": "fullstack_dev.txt"})], "התמקדי ב-C# ו-Angular")
        + step([("save_memory", {"key": "interview_format", "value": "ראיון מוקלט מול מצלמה"}),
                ("save_memory", {"key": "excluded_topics", "value": "sql"})], "שמרתי")
        + step([("get_questions", {"topic": "csharp", "limit": 1})], "cs01")
        + step([("log_practice", {"question_id": "cs01", "confidence": 2, "note": "interface"})], "נרשם")
        + step([("get_progress", {})], "הראיון מוקלט, ותרגלת C#")
        + step([("save_memory", {"key": "excluded_topics", "value": ""}),
                ("get_questions", {"topic": "sql", "limit": 1})], "sq01")
        + step([("log_practice", {"question_id": "sq01", "confidence": 4}), ("get_progress", {})], "סיכום")
    )


def test_full_scenario_offline(tmp_path, store):
    client = FakeClient(scripted_responses())
    out = tmp_path / "api.json"

    def make_agent(i):
        return Agent(client, store, f"session{i}", "claude-opus-5-5", "medium")

    result = asyncio.run(run_scenario(ROOT / "scenario.json", out, "API", make_agent, store,
                                      {"total_harness": 0}, {"model": "fake"}))

    assert all(c["passed"] for c in result["checks"]), result["checks"]
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert len(saved["turns"]) == 7
    assert set(saved["turns"][0]["tokens"]) == {"input", "cache_read", "cache_write", "output"}
