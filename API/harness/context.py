"""מה נכנס לכל קריאה למודל.

נדחף (push), כי קטן ותמיד רלוונטי:
    1. הוראות קבועות (shared/prompts.py)
    2. הזיכרון של המשתמשת, כפי שנטען בתחילת הסשן
    3. הגדרות 5 הכלים
    4. השיחה הנוכחית (אחרי compaction)
נשלף (pull) בכלים רק כשצריך: בנק השאלות, יומן התרגול, קובץ המשרה.
מה שמשתנה בכל קריאה (כמו שעה) לא נכנס, כדי לא לשבור את ה-cache.
"""
from shared.prompts import SYSTEM_PROMPT

from . import log


def build(model, effort, max_tokens, memory_text, tool_schemas, messages):
    request = {
        "model": model,
        "max_tokens": max_tokens,
        "output_config": {"effort": effort},
        "system": [
            {"type": "text", "text": SYSTEM_PROMPT},  # קבוע לגמרי
            {"type": "text", "text": memory_text},    # קבוע לאורך הסשן
        ],
        "tools": tool_schemas,
        "messages": messages,
    }
    chars = len(SYSTEM_PROMPT) + len(memory_text)
    log(__file__, f"system={chars} chars, tools={len(tool_schemas)}, messages={len(messages)}")
    return request
