"""client מדומה: מחזיר תשובות מוכנות מראש במקום לפנות ל-Claude. בלי מפתח, בלי אינטרנט, בלי עלות."""
import copy
from types import SimpleNamespace


class Block(SimpleNamespace):
    def model_dump(self, exclude_none=True):
        return {k: v for k, v in vars(self).items() if not (exclude_none and v is None)}


def text(t):
    return Block(type="text", text=t)


def tool_use(id_, name, input_):
    return Block(type="tool_use", id=id_, name=name, input=input_)


def response(blocks, stop_reason, input_tokens=100, cache_read=0, cache_write=0, output=20):
    usage = SimpleNamespace(input_tokens=input_tokens, cache_read_input_tokens=cache_read,
                            cache_creation_input_tokens=cache_write, output_tokens=output)
    return SimpleNamespace(content=blocks, stop_reason=stop_reason, usage=usage)


class FakeClient:
    """מחזיר את התשובות לפי הסדר, ושומר העתק של כל בקשה כדי שהבדיקות יבדקו מה נשלח."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []
        self.messages = self  # כדי ש-client.messages.create יעבוד

    def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        if not self._responses:
            raise AssertionError("FakeClient: אין עוד תשובות מוכנות")
        return self._responses.pop(0)
