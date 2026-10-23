"""מצב הסוכן שנשמר לדיסק: זיכרון ארוך-טווח ויומן תרגול.

שתי הגרסאות (API ו-SDK) משתמשות באותו פורמט, כל אחת בתיקיית state משלה.
"""
import json
import shutil
from pathlib import Path


class Store:
    def __init__(self, state_dir):
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.memory_path = self.dir / "memory.json"
        self.practice_path = self.dir / "practice.json"

    # ---------- קריאה/כתיבה בסיסית ----------
    def _read(self, path, default):
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path, data):
        # כתיבה לקובץ זמני ואז החלפה, כדי שקריסה באמצע לא תשאיר קובץ שבור
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    # ---------- זיכרון ----------
    def load_memory(self):
        return self._read(self.memory_path, {})

    def save_memory(self, memory):
        self._write(self.memory_path, memory)

    # ---------- יומן תרגול ----------
    def load_practice(self):
        return self._read(self.practice_path, [])

    def save_practice(self, entries):
        self._write(self.practice_path, entries)

    # ---------- עזרים לתרחיש ולבדיקות ----------
    def snapshot(self):
        return {"memory": self.load_memory(), "practice": self.load_practice()}

    def reset(self):
        """מצב נקי: מוחק את כל תיקיית ה-state."""
        if self.dir.exists():
            shutil.rmtree(self.dir)
        self.dir.mkdir(parents=True, exist_ok=True)
