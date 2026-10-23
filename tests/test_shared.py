"""בדיקות לקוד הדומיין ב-shared/ (הכלים עצמם)."""
import pytest

from shared.domain import ToolError, run_tool


def test_get_questions_filters_topic_and_skips_practiced(store):
    first = run_tool(store, "get_questions", {"topic": "csharp", "limit": 1})
    assert first.startswith("cs01")
    run_tool(store, "log_practice", {"question_id": "cs01", "confidence": 3})
    second = run_tool(store, "get_questions", {"topic": "csharp", "limit": 1})
    assert second.startswith("cs02")  # cs01 כבר תורגלה


def test_unknown_topic_is_tool_error(store):
    with pytest.raises(ToolError):
        run_tool(store, "get_questions", {"topic": "cobol"})


def test_log_practice_validates(store):
    with pytest.raises(ToolError):
        run_tool(store, "log_practice", {"question_id": "zz99", "confidence": 3})
    with pytest.raises(ToolError):
        run_tool(store, "log_practice", {"question_id": "cs01", "confidence": 9})
    assert store.load_practice() == []


def test_save_memory_overwrites_same_key_and_deletes_on_empty(store):
    run_tool(store, "save_memory", {"key": "excluded_topics", "value": "sql"})
    out = run_tool(store, "save_memory", {"key": "excluded_topics", "value": "angular"})
    assert "היה: 'sql'" in out
    assert store.load_memory() == {"excluded_topics": "angular"}  # עודכן, לא נוסף
    run_tool(store, "save_memory", {"key": "excluded_topics", "value": ""})
    assert store.load_memory() == {}


def test_read_job_description_blocks_path_traversal(store):
    assert "Full Stack" in run_tool(store, "read_job_description", {"filename": "fullstack_dev.txt"})
    with pytest.raises(ToolError):
        run_tool(store, "read_job_description", {"filename": "../scenario.json"})


def test_progress_is_compact(store):
    run_tool(store, "log_practice", {"question_id": "cs01", "confidence": 2, "note": "interface"})
    run_tool(store, "log_practice", {"question_id": "sq01", "confidence": 4})
    out = run_tool(store, "get_progress", {})
    assert out.splitlines()[0].startswith("csharp")  # החלש ראשון
    assert len(out) < 200


def test_missing_required_param_is_tool_error(store):
    with pytest.raises(ToolError):
        run_tool(store, "log_practice", {"question_id": "cs01"})
