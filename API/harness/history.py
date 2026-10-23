"""היסטוריית השיחה: נשמרת לדיסק כ-JSONL, append-only.

כל שורה היא אחת מאלה:
    {"kind": "message", "message": {...}}                     הודעה בשיחה
    {"kind": "compaction", "summarized": N, "summary": "..."}  סימון שבוצע compaction
הקובץ לעולם לא נמחק או נכתב מחדש. compaction רק מוסיף שורה, וכך אפשר לשחזר
גם את השיחה המלאה וגם את מה שנשלח בפועל למודל.
"""
import json
from pathlib import Path

from . import log


class History:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _append(self, record):
        with open(self.path, "a", encoding="utf-8") as f:  # "a" = רק הוספה לסוף
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def append(self, message):
        self._append({"kind": "message", "message": message})
        log(__file__, f"appended {message['role']} message -> {self.path.name}")

    def append_compaction(self, summarized, summary):
        self._append({"kind": "compaction", "summarized": summarized, "summary": summary})
        log(__file__, f"appended compaction marker ({summarized} messages summarized)")

    def records(self):
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def load_working(self):
        """משחזר את רשימת ההודעות שנשלחת למודל (אחרי כל ה-compactions), להמשך שיחה."""
        from .compaction import merge_summary  # import מקומי כדי למנוע מעגל
        messages = []
        for r in self.records():
            if r["kind"] == "message":
                messages.append(r["message"])
            else:
                messages = merge_summary(r["summary"], messages[r["summarized"]:])
        log(__file__, f"resumed {len(messages)} working messages from {self.path.name}")
        return messages
