"""הסוכן בגרסת ה-API: מחבר את כל קבצי ה-harness לתור אחד."""
from pathlib import Path

from API.harness import caching, compaction, context, loop, memory
from API.harness.history import History
from API.harness.tokens import TurnUsage
from API.harness.tools import ToolBox


class Agent:
    def __init__(self, client, store, session_name, model, effort,
                 max_tokens=16000, compaction_threshold=20000, resume=False):
        self.client = client
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self.threshold = compaction_threshold
        self.toolbox = ToolBox(store)
        self.history = History(Path(store.dir) / "sessions" / f"{session_name}.jsonl")
        self.messages = self.history.load_working() if resume else []
        self.memory_text = memory.load_for_session(store)  # פעם אחת לסשן
        self.last_context_tokens = 0

    def _request(self):
        req = context.build(self.model, self.effort, self.max_tokens,
                            self.memory_text, self.toolbox.schemas, self.messages)
        return caching.apply(req)

    def turn(self, user_text):
        usage = TurnUsage(self.model)
        self.messages = compaction.maybe_compact(
            self.client, self.model, self.messages, self.last_context_tokens,
            self.threshold, self.history, usage)

        user_message = {"role": "user", "content": user_text}
        self.messages.append(user_message)
        self.history.append(user_message)

        text, tools = loop.run(self.client, self._request, self.messages, self.toolbox, self.history, usage)
        self.last_context_tokens = usage.last_context_tokens
        return {
            "response": text,
            "tokens": usage.tokens,
            "model_calls": usage.calls,
            "tools": tools,
            "cost_usd": usage.cost_usd,
        }
