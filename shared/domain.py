"""קוד הדומיין: הכלים של סוכן ההכנה לראיונות.

כל כלי מוגדר פעם אחת כאן:
- TOOL_SPECS: שם, תיאור וסכמת JSON (ניטרלי, לא תלוי ב-API או ב-SDK)
- הפונקציה עצמה: מחזירה מחרוזת קצרה (פלט קומפקטי = פחות טוקנים)
- שגיאה = ToolError, וכל harness מחזיר אותה למודל כ-is_error

ה-API וה-SDK רק עוטפים את מה שכאן.
"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = json.loads((ROOT / "shared" / "data" / "questions.json").read_text(encoding="utf-8"))
QUESTIONS_BY_ID = {q["id"]: q for q in QUESTIONS}
TOPICS = sorted({q["topic"] for q in QUESTIONS})
JOBS_DIR = ROOT / "job_descriptions"
MEMORY_KEYS = ["target_role", "interview_format", "excluded_topics", "focus_topics", "answer_style", "notes"]
MAX_JOB_CHARS = 1500


class ToolError(Exception):
    """שגיאה שהמודל צריך לראות (ולתקן), לא קריסה של התוכנית."""


# ---------------------------------------------------------------- הכלים

def get_questions(store, topic, limit=2):
    if topic not in TOPICS:
        raise ToolError(f"נושא לא קיים: {topic}. נושאים: {', '.join(TOPICS)}")
    limit = max(1, min(int(limit), 5))
    practiced = {e["question_id"] for e in store.load_practice()}
    fresh = [q for q in QUESTIONS if q["topic"] == topic and q["id"] not in practiced]
    if not fresh:
        return f"אין שאלות חדשות בנושא {topic} (כולן תורגלו)."
    return "\n".join(f"{q['id']} | {q['text']}" for q in fresh[:limit])


def log_practice(store, question_id, confidence, note=""):
    q = QUESTIONS_BY_ID.get(question_id)
    if q is None:
        raise ToolError(f"מזהה שאלה לא קיים: {question_id}")
    confidence = int(confidence)
    if not 1 <= confidence <= 5:
        raise ToolError("confidence חייב להיות בין 1 ל-5")
    entries = store.load_practice()
    entries.append({
        "question_id": question_id,
        "topic": q["topic"],
        "confidence": confidence,
        "note": note[:200],
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    store.save_practice(entries)
    return f"נרשם: {question_id} ({q['topic']}) ביטחון {confidence}/5"


def get_progress(store, topic=None):
    entries = store.load_practice()
    if topic:
        entries = [e for e in entries if e["topic"] == topic]
    if not entries:
        return "עדיין אין תרגולים" + (f" בנושא {topic}." if topic else ".")
    by_topic = {}
    for e in entries:
        by_topic.setdefault(e["topic"], []).append(e["confidence"])
    lines = []
    for t, scores in sorted(by_topic.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
        lines.append(f"{t}: {len(scores)} תרגולים, ממוצע ביטחון {sum(scores) / len(scores):.1f}/5")
    last = entries[-1]
    lines.append(f"אחרון: {last['question_id']} ({last['confidence']}/5) {last['note']}".strip())
    return "\n".join(lines)


def read_job_description(store, filename):
    # הכלי החיצוני: קורא קובץ מהדיסק, רק מתוך תיקיית job_descriptions
    path = (JOBS_DIR / filename).resolve()
    if path.parent != JOBS_DIR.resolve() or not path.is_file():
        available = ", ".join(p.name for p in sorted(JOBS_DIR.glob("*.txt"))) or "אין"
        raise ToolError(f"קובץ לא נמצא: {filename}. קבצים זמינים: {available}")
    text = path.read_text(encoding="utf-8").strip()
    if len(text) > MAX_JOB_CHARS:
        text = text[:MAX_JOB_CHARS] + "\n...[קוצר]"
    return text


def save_memory(store, key, value):
    if key not in MEMORY_KEYS:
        raise ToolError(f"מפתח לא חוקי: {key}. מפתחות: {', '.join(MEMORY_KEYS)}")
    memory = store.load_memory()
    old = memory.get(key)
    value = value.strip()
    if value:
        memory[key] = value  # אותו מפתח = עדכון, לא עובדה כפולה
    else:
        memory.pop(key, None)  # ערך ריק = מחיקה
    store.save_memory(memory)
    return f"זיכרון: {key} = '{value}'" + (f" (היה: '{old}')" if old else "")


# ---------------------------------------------------------------- הגדרות

TOOL_SPECS = [
    {
        "name": "get_questions",
        "description": "מחזיר שאלות ראיון שעוד לא תורגלו, בנושא אחד. השתמשי כשהמשתמשת מבקשת שאלות לתרגול.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "enum": TOPICS, "description": "נושא השאלות"},
                "limit": {"type": "integer", "description": "כמה שאלות (1-5)", "default": 2},
            },
            "required": ["topic"],
        },
        "fn": get_questions,
    },
    {
        "name": "log_practice",
        "description": "רושם שהמשתמשת תרגלה שאלה, עם רמת הביטחון שלה (1-5) והערה קצרה. השתמשי אחרי שהיא עונה או מדווחת שענתה.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question_id": {"type": "string", "description": "מזהה השאלה, למשל cs01"},
                "confidence": {"type": "integer", "description": "1 = לא בטוחה בכלל, 5 = בטוחה מאוד"},
                "note": {"type": "string", "description": "הערה קצרה: במה התבלבלה או מה לחזק"},
            },
            "required": ["question_id", "confidence"],
        },
        "fn": log_practice,
    },
    {
        "name": "get_progress",
        "description": "סיכום קצר של התרגול: כמה תרגולים וממוצע ביטחון לכל נושא, מהחלש לחזק. השתמשי כששואלים על התקדמות או איפה עצרנו.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "enum": TOPICS, "description": "אופציונלי: רק נושא אחד"},
            },
        },
        "fn": get_progress,
    },
    {
        "name": "read_job_description",
        "description": "קורא קובץ תיאור משרה מתיקיית job_descriptions בדיסק. השתמשי כשהמשתמשת מזכירה קובץ משרה.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "שם הקובץ, למשל fullstack_dev.txt"},
            },
            "required": ["filename"],
        },
        "fn": read_job_description,
    },
    {
        "name": "save_memory",
        "description": (
            "שומר או מעדכן עובדה ארוכת טווח על המשתמשת, כדי לזכור בסשנים הבאים. "
            "השתמשי מיד כשהיא מציינת העדפה, החלטה או שינוי בהחלטה קודמת. "
            "אותו מפתח דורס את הערך הקודם; ערך ריק מוחק. "
            f"עבור excluded_topics ו-focus_topics: רשימת מזהי נושאים מופרדת בפסיקים מתוך: {', '.join(TOPICS)}."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "enum": MEMORY_KEYS},
                "value": {"type": "string", "description": "הערך החדש (ריק = מחיקה)"},
            },
            "required": ["key", "value"],
        },
        "fn": save_memory,
    },
]

SPECS_BY_NAME = {s["name"]: s for s in TOOL_SPECS}


def run_tool(store, name, args):
    """הרצה אחידה לשני ה-harnesses. זורק ToolError על כל בעיה."""
    spec = SPECS_BY_NAME.get(name)
    if spec is None:
        raise ToolError(f"כלי לא קיים: {name}")
    try:
        return spec["fn"](store, **args)
    except TypeError as e:  # פרמטר חסר או מיותר
        raise ToolError(f"פרמטרים לא תקינים ל-{name}: {e}") from e
