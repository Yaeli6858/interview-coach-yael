"""זיכרון ארוך-טווח: איפה הוא נשמר ואיך שולפים ממנו.

- נשמר ב-state/api/memory.json (מפתח -> ערך), דרך הכלי save_memory (shared/domain.py).
- נשלף פעם אחת בתחילת כל סשן ונדחף ל-system prompt, כי הוא קטן ותמיד רלוונטי.
- לא נטען מחדש באמצע סשן: שינוי באמצע כבר ידוע למודל מתוצאת הכלי,
  וטעינה מחדש הייתה משנה את ה-prefix ושוברת את ה-cache.
"""
from shared.prompts import memory_block

from . import log


def load_for_session(store):
    memory = store.load_memory()
    log(__file__, f"loaded {len(memory)} facts from {store.memory_path}: {sorted(memory)}")
    return memory_block(memory)
