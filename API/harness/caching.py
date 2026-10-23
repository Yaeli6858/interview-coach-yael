"""Prompt caching: איפה שמים נקודות cache_control.

סדר ה-prefix ב-API: tools -> system -> messages. כל נקודה שומרת את כל מה שלפניה.
שלוש נקודות (המקסימום הוא 4):
    1. סוף ההוראות הקבועות  -> tools + system, זהה בכל הסשנים
    2. סוף בלוק הזיכרון     -> קבוע לאורך סשן
    3. הבלוק האחרון בשיחה   -> בקריאה הבאה כל השיחה עד כאן נקראת מה-cache
לא משנים את הרשימה המקורית: אם הנקודות היו נשמרות בהודעות, הן היו מצטברות מעבר ל-4.
(ל-Opus 5.5 מינימום 512 טוקנים לקטע שנשמר; קצר מזה פשוט לא נשמר, בלי שגיאה.)
"""
import copy

from . import log

CACHE = {"type": "ephemeral"}


def apply(request):
    req = dict(request)
    system = copy.deepcopy(request["system"])
    system[0]["cache_control"] = CACHE
    system[-1]["cache_control"] = CACHE
    req["system"] = system

    messages = list(request["messages"])
    if messages:
        last = copy.deepcopy(messages[-1])
        if isinstance(last["content"], str):
            last["content"] = [{"type": "text", "text": last["content"]}]
        last["content"][-1]["cache_control"] = CACHE
        messages[-1] = last
    req["messages"] = messages

    marks = 2 + (1 if messages else 0)
    log(__file__, f"{marks} cache breakpoints: system-static, system-memory" + (", last message" if messages else ""))
    return req
