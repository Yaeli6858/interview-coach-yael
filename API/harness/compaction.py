"""חלון קונטקסט: כשהשיחה עוברת סף, מסכמים את החלק הישן ומחליפים אותו בסיכום.

- רץ בתחילת תור של המשתמשת, לא באמצע לולאת כלים, כך שזוג tool_use/tool_result אף פעם לא נחתך.
- גודל הקונטקסט נלקח מה-usage של הקריאה האחרונה (input + cache read + cache write).
- נשארים 2 התורות האחרונים של המשתמשת במלואם; כל מה שלפניהם הופך לסיכום.
- הסיכום מוצמד כבלוק טקסט להודעת המשתמשת הראשונה שנשארה, כדי לשמור על סדר user/assistant.
"""
import json

from . import log

SUMMARY_PROMPT = (
    "סכמי את השיחה הבאה בין מאמנת ראיונות למשתמשת, בעברית, עד 8 שורות. "
    "שמרי: החלטות, העדפות, אילו שאלות תורגלו ובאיזה ביטחון, ומה עוד פתוח."
)


def _is_new_user_input(message):
    if message["role"] != "user":
        return False
    content = message["content"]
    if isinstance(content, str):
        return True
    return not any(b.get("type") == "tool_result" for b in content)


def _render(messages):
    """הופך הודעות לטקסט קריא לסיכום (בלי thinking, תוצאות כלים מקוצרות)."""
    lines = []
    for m in messages:
        content = m["content"]
        if isinstance(content, str):
            lines.append(f"{m['role']}: {content}")
            continue
        for b in content:
            kind = b.get("type")
            if kind == "text":
                lines.append(f"{m['role']}: {b['text']}")
            elif kind == "tool_use":
                lines.append(f"tool_use: {b['name']}({json.dumps(b['input'], ensure_ascii=False)})")
            elif kind == "tool_result":
                text = b["content"] if isinstance(b["content"], str) else json.dumps(b["content"], ensure_ascii=False)
                lines.append(f"tool_result: {text[:300]}")
    return "\n".join(lines)


def merge_summary(summary, kept):
    """מצמיד את הסיכום להודעה הראשונה שנשארה (חייבת להיות קלט חדש של המשתמשת)."""
    first, rest = kept[0], kept[1:]
    original = first["content"]
    blocks = [{"type": "text", "text": original}] if isinstance(original, str) else list(original)
    merged = {"role": "user", "content": [{"type": "text", "text": f"[סיכום השיחה עד כה]\n{summary}"}] + blocks}
    return [merged] + rest


def maybe_compact(client, model, messages, context_tokens, threshold, history, usage, keep_user_turns=2):
    if context_tokens < threshold:
        log(__file__, f"context {context_tokens} < threshold {threshold}: no compaction")
        return messages
    starts = [i for i, m in enumerate(messages) if _is_new_user_input(m)]
    if len(starts) <= keep_user_turns:
        log(__file__, "over threshold but too few turns to compact")
        return messages
    cut = starts[-keep_user_turns]
    response = client.messages.create(
        model=model,
        max_tokens=1500,
        output_config={"effort": "low"},  # סיכום הוא משימה פשוטה
        system=SUMMARY_PROMPT,
        messages=[{"role": "user", "content": _render(messages[:cut])}],
    )
    usage.add(response.usage, label="compaction")
    summary = "".join(b.text for b in response.content if b.type == "text").strip()
    history.append_compaction(cut, summary)
    log(__file__, f"compacted {cut} messages into {len(summary)} chars (context was {context_tokens})")
    return merge_summary(summary, messages[cut:])
