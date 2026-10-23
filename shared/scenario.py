"""הרצת scenario.json ובדיקות pass/fail. משותף ל-API ול-SDK, כדי ששתיהן יימדדו באותה דרך.

סוכן (מכל גרסה) צריך לספק:
    agent.turn(text) -> dict עם response, tokens{input,cache_read,cache_write,output},
                        model_calls, tools(list), cost_usd
    agent.close()    -> אופציונלי
הפונקציות יכולות להיות רגילות או async.
"""
import inspect
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN_KEYS = ["input", "cache_read", "cache_write", "output"]


async def _maybe_await(x):
    return await x if inspect.isawaitable(x) else x


async def run_scenario(scenario_path, out_path, version, make_agent, store, lines_of_code, meta):
    scenario = json.loads(Path(scenario_path).read_text(encoding="utf-8"))
    store.reset()  # כל ריצה מתחילה ממצב נקי
    turns, snapshots = [], {}

    for s_index, session in enumerate(scenario["sessions"], start=1):
        print(f"\n===== {version}: session {s_index} (מופע חדש של הסוכן) =====")
        agent = await _maybe_await(make_agent(s_index))  # מופע חדש: טוען מהדיסק רק את מה שנשמר
        try:
            for user_text in session["turns"]:
                print(f"\n>>> {user_text}")
                start = time.perf_counter()
                result = await _maybe_await(agent.turn(user_text))
                seconds = round(time.perf_counter() - start, 2)
                print(f"<<< {result['response']}")
                turns.append({
                    "session": s_index,
                    "turn": len(turns) + 1,
                    "user": user_text,
                    "response": result["response"],
                    "tokens": result["tokens"],
                    "model_calls": result["model_calls"],
                    "tools": result["tools"],
                    "cost_usd": round(result["cost_usd"], 6),
                    "seconds": seconds,
                })
        finally:
            if hasattr(agent, "close"):
                await _maybe_await(agent.close())
        snapshots[s_index] = store.snapshot()

    checks = evaluate_checks(scenario.get("checks", []), snapshots, turns)
    totals = summarize(turns)
    output = {
        "version": version,
        **meta,
        "totals": totals,
        "checks": checks,
        "checks_passed": f"{sum(c['passed'] for c in checks)}/{len(checks)}",
        "lines_of_code": lines_of_code,
        "turns": turns,
        "final_state": snapshots[max(snapshots)],
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n===== {version}: סיכום =====")
    print(json.dumps(totals, ensure_ascii=False))
    for c in checks:
        print(("PASS " if c["passed"] else "FAIL ") + c["name"] + (f"  ({c['detail']})" if not c["passed"] else ""))
    print(f"נשמר: {out_path}")
    return output


def summarize(turns):
    tok = {k: sum(t["tokens"][k] for t in turns) for k in TOKEN_KEYS}
    all_input = tok["input"] + tok["cache_read"] + tok["cache_write"]
    return {
        "tokens": tok,
        "cache_hit_pct": round(100 * tok["cache_read"] / all_input, 1) if all_input else 0.0,
        "model_calls": sum(t["model_calls"] for t in turns),
        "cost_usd": round(sum(t["cost_usd"] for t in turns), 6),
        "seconds": round(sum(t["seconds"] for t in turns), 2),
    }


# ---------------------------------------------------------------- בדיקות

def _topics(value):
    return {t.strip().lower() for t in (value or "").split(",") if t.strip()}


def _check(check, snapshots, turns):
    kind = check["type"]
    if kind in ("memory_has_topic", "memory_lacks_topic"):
        mem = snapshots[check["after_session"]]["memory"]
        topics = _topics(mem.get(check["key"]))
        has = check["topic"].lower() in topics
        ok = has if kind == "memory_has_topic" else not has
        return ok, f"{check['key']}={mem.get(check['key'])!r}"
    if kind == "memory_contains_any":
        mem = snapshots[check["after_session"]]["memory"]
        value = (mem.get(check["key"]) or "").lower()
        ok = any(w.lower() in value for w in check["values"])
        return ok, f"{check['key']}={mem.get(check['key'])!r}"
    if kind == "practice_logged":
        entries = snapshots[check["after_session"]]["practice"]
        match = [e for e in entries
                 if e["topic"] == check["topic"]
                 and ("confidence" not in check or e["confidence"] == check["confidence"])]
        return len(match) >= check.get("min", 1), f"{len(match)} matching of {len(entries)}"
    if kind == "tool_called":
        used = [t for x in turns if x["session"] == check["session"] for t in x["tools"]]
        return check["tool"] in used, f"tools in session {check['session']}: {used}"
    if kind == "response_contains_any":
        text = turns[check["turn"] - 1]["response"].lower()
        return any(w.lower() in text for w in check["values"]), "response text"
    raise ValueError(f"unknown check type: {kind}")


def evaluate_checks(checks, snapshots, turns):
    results = []
    for check in checks:
        try:
            ok, detail = _check(check, snapshots, turns)
        except (KeyError, IndexError) as e:
            ok, detail = False, f"error: {e}"
        results.append({"name": check["name"], "type": check["type"], "passed": bool(ok), "detail": detail})
    return results


# ---------------------------------------------------------------- שורות קוד

def count_code_lines(path):
    """שורות קוד בלבד: בלי שורות ריקות, הערות ו-docstrings."""
    count, in_doc = 0, False
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if in_doc:
            if line.endswith('"""'):
                in_doc = False
            continue
        if line.startswith('"""'):
            if not (len(line) > 3 and line.endswith('"""')):
                in_doc = True
            continue
        if line and not line.startswith("#"):
            count += 1
    return count
