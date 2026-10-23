"""טוקנים ועלות לכל תור (תור אחד = כמה קריאות למודל).

מחירים ב-USD למיליון טוקנים, מעמוד התמחור הרשמי:
https://platform.claude.com/docs/en/about-claude/pricing  (נבדק 2026-10-23)
cache_write = כתיבה ל-cache של 5 דקות (ברירת המחדל של ephemeral).
"""
from . import log

PRICES = {
    "claude-opus-5-5": {"input": 4.00, "cache_write": 5.00, "cache_read": 0.20, "output": 20.00},
}


def _get(usage, name):
    return getattr(usage, name, None) or 0


class TurnUsage:
    def __init__(self, model):
        if model not in PRICES:
            raise ValueError(f"אין מחיר למודל {model}. הוסיפי אותו ל-PRICES ב-tokens.py")
        self.price = PRICES[model]
        self.tokens = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
        self.calls = 0
        self.last_context_tokens = 0  # גודל הקונטקסט בקריאה האחרונה, בשביל compaction

    def add(self, usage, label="agent"):
        call = {
            "input": _get(usage, "input_tokens"),
            "cache_read": _get(usage, "cache_read_input_tokens"),
            "cache_write": _get(usage, "cache_creation_input_tokens"),
            "output": _get(usage, "output_tokens"),
        }
        for k, v in call.items():
            self.tokens[k] += v
        self.calls += 1
        if label == "agent":
            self.last_context_tokens = call["input"] + call["cache_read"] + call["cache_write"]
        log(__file__, f"{label} call: in={call['input']} cache_read={call['cache_read']} "
                      f"cache_write={call['cache_write']} out={call['output']} ${self._cost(call):.4f}")

    def _cost(self, t):
        return sum(t[k] * self.price[k] for k in t) / 1_000_000

    @property
    def cost_usd(self):
        return self._cost(self.tokens)
