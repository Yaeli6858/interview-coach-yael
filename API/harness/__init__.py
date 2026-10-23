"""ה-harness של גרסת ה-API: קובץ אחד לכל אחריות."""
from pathlib import Path


def log(module_file, message):
    """כל פעולה בזמן ריצה מודפסת עם שם הקובץ שביצע אותה (דרישת התרגיל)."""
    print(f"  [{Path(module_file).name}] {message}")


def block_to_dict(block):
    """ממיר בלוק תוכן מתשובת ה-API ל-dict, כדי לשמור בהיסטוריה ולשלוח שוב."""
    if isinstance(block, dict):
        return block
    return block.model_dump(exclude_none=True)
