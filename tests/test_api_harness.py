"""בדיקות offline ל-harness של ה-API, עם client מדומה."""
import json

from fakes import FakeClient, response, text, tool_use

from API.agent import Agent
from API.harness import caching, compaction
from API.harness.history import History
from API.harness.tokens import TurnUsage

MODEL, EFFORT = "claude-opus-5-5", "medium"


def make_agent(client, store, **kw):
    return Agent(client, store, "s1", MODEL, EFFORT, **kw)


def test_loop_runs_tools_and_returns_all_results_in_one_message(store):
    client = FakeClient([
        response([tool_use("t1", "get_questions", {"topic": "csharp", "limit": 1}),
                  tool_use("t2", "get_progress", {})], "tool_use"),
        response([text("הנה שאלה")], "end_turn"),
    ])
    result = make_agent(client, store).turn("תני שאלה")

    assert result["response"] == "הנה שאלה"
    assert result["tools"] == ["get_questions", "get_progress"]
    assert result["model_calls"] == 2
    tool_msg = client.requests[1]["messages"][-1]  # ההודעה האחרונה בקריאה השנייה
    assert tool_msg["role"] == "user"
    assert [b["tool_use_id"] for b in tool_msg["content"]] == ["t1", "t2"]
    assert all(b["type"] == "tool_result" for b in tool_msg["content"])


def test_tool_error_goes_back_to_model_as_is_error(store):
    client = FakeClient([
        response([tool_use("t1", "log_practice", {"question_id": "nope", "confidence": 3})], "tool_use"),
        response([text("מזהה לא נכון")], "end_turn"),
    ])
    make_agent(client, store).turn("תרשמי")
    result_block = client.requests[1]["messages"][-1]["content"][0]
    assert result_block["is_error"] is True
    assert "nope" in result_block["content"]


def test_request_has_model_effort_memory_and_cache_breakpoints(store):
    store.save_memory({"excluded_topics": "sql"})
    client = FakeClient([response([text("שלום")], "end_turn")])
    make_agent(client, store).turn("היי")
    req = client.requests[0]
    assert req["model"] == MODEL and req["output_config"] == {"effort": EFFORT}
    assert "excluded_topics: sql" in req["system"][1]["text"]  # הזיכרון נדחף ל-system
    marks = json.dumps(req).count('"cache_control"')
    assert marks == 3 and marks <= 4


def test_caching_does_not_mutate_stored_messages():
    request = {"system": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}],
               "messages": [{"role": "user", "content": "שלום"}]}
    cached = caching.apply(request)
    assert request["messages"][0]["content"] == "שלום"  # המקור לא השתנה
    assert cached["messages"][0]["content"][-1]["cache_control"] == {"type": "ephemeral"}


def test_history_is_append_only_and_resumable(store):
    client = FakeClient([response([text("א")], "end_turn"), response([text("ב")], "end_turn")])
    agent = make_agent(client, store)
    agent.turn("1")
    path = agent.history.path
    first_lines = path.read_text(encoding="utf-8").splitlines()
    agent.turn("2")
    all_lines = path.read_text(encoding="utf-8").splitlines()
    assert all_lines[:len(first_lines)] == first_lines  # שורות ישנות לא השתנו
    assert len(all_lines) == 4

    resumed = make_agent(FakeClient([]), store, resume=True)
    assert [m["role"] for m in resumed.messages] == ["user", "assistant", "user", "assistant"]


def test_compaction_summarizes_old_turns_over_threshold(store):
    usage = TurnUsage(MODEL)
    history = History(store.dir / "h.jsonl")
    messages = []
    for i in range(3):
        messages += [{"role": "user", "content": f"שאלה {i}"},
                     {"role": "assistant", "content": [{"type": "text", "text": f"תשובה {i}"}]}]
    client = FakeClient([response([text("סיכום קצר")], "end_turn")])

    out = compaction.maybe_compact(client, MODEL, messages, 50000, 1000, history, usage)

    # 6 הודעות -> תור 0 מסוכם, 2 התורות האחרונים נשארים: [סיכום+שאלה 1, תשובה 1, שאלה 2, תשובה 2]
    assert len(out) == 4
    assert out[0]["content"][0]["text"].endswith("סיכום קצר")
    assert out[0]["content"][1]["text"] == "שאלה 1"
    assert usage.calls == 1  # קריאת הסיכום נספרת
    assert history.records()[-1]["kind"] == "compaction"


def test_compaction_skipped_under_threshold(store):
    messages = [{"role": "user", "content": "x"}]
    out = compaction.maybe_compact(FakeClient([]), MODEL, messages, 10, 1000,
                                   History(store.dir / "h.jsonl"), TurnUsage(MODEL))
    assert out is messages


def test_token_cost_uses_opus_prices():
    usage = TurnUsage(MODEL)
    fake = response([], "end_turn", input_tokens=1_000_000, cache_read=1_000_000,
                    cache_write=1_000_000, output=1_000_000).usage
    usage.add(fake)
    assert round(usage.cost_usd, 2) == 4.00 + 0.20 + 5.00 + 20.00
