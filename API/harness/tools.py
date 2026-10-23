"""כלים: סכמות JSON בפורמט של ה-Messages API, dispatch, ושגיאות שחוזרות למודל כ-is_error."""
from shared.domain import TOOL_SPECS, ToolError, run_tool

from . import log


class ToolBox:
    def __init__(self, store):
        self.store = store
        # הסכמות נשלחות בכל קריאה. סדר קבוע = prefix קבוע = cache עובד
        self.schemas = [
            {"name": s["name"], "description": s["description"], "input_schema": s["input_schema"]}
            for s in TOOL_SPECS
        ]

    def execute(self, tool_use_id, name, args):
        """מריץ כלי אחד ומחזיר בלוק tool_result. לעולם לא זורק: כל שגיאה חוזרת למודל."""
        try:
            output = run_tool(self.store, name, args)
            log(__file__, f"{name}({args}) -> {len(output)} chars")
            return {"type": "tool_result", "tool_use_id": tool_use_id, "content": output}
        except ToolError as e:
            log(__file__, f"{name}({args}) -> is_error: {e}")
            return {"type": "tool_result", "tool_use_id": tool_use_id, "content": str(e), "is_error": True}
        except Exception as e:  # באג בכלי: המודל מקבל הודעה, הסוכן ממשיך
            log(__file__, f"{name}({args}) -> unexpected error: {e!r}")
            return {"type": "tool_result", "tool_use_id": tool_use_id,
                    "content": f"שגיאה פנימית בכלי {name}", "is_error": True}
