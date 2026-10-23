"""הסוכן בגרסת ה-SDK: רק הגדרות. Claude Code מריץ את ה-harness.

caching.py ו-compaction.py: אין קוד בכלל. Claude Code עושה אותם אוטומטית.
"""
from pathlib import Path

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient,
                              ResultMessage, SystemMessage, ToolUseBlock)

from shared.prompts import SYSTEM_PROMPT, memory_block
from SDK.tools import ALLOWED_TOOLS, SERVER_NAME, build_server

ROOT = Path(__file__).resolve().parent.parent
PREFIX = f"mcp__{SERVER_NAME}__"


class Agent:
    def __init__(self, client, store):
        self.client = client
        self.store = store
        self.prev_cost = 0.0  # total_cost_usd מצטבר לאורך ה-client, אז שומרים את הקודם
        self.session_id = None

    @classmethod
    async def create(cls, store, model, effort, resume_session_id=None):
        memory = store.load_memory()
        print(f"  [SDK/agent.py] loaded {len(memory)} facts from {store.memory_path}: {sorted(memory)}")
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT + "\n\n" + memory_block(memory),  # replaces: context.py, memory.py
            mcp_servers={SERVER_NAME: build_server(store)},  # replaces: tools.py
            tools=[],  # בלי כלים מובנים של Claude Code. מאומת בהדפסת init למטה
            allowed_tools=ALLOWED_TOOLS,  # replaces: tools.py
            strict_mcp_config=True,  # רק השרת שלנו, בלי שרתי MCP מהגדרות המחשב
            setting_sources=[],  # לא לטעון CLAUDE.md והגדרות מהמחשב: קונטקסט נקי והשוואה הוגנת
            model=model,
            effort=effort,
            max_turns=10,  # replaces: loop.py
            resume=resume_session_id,  # replaces: history.py
            cwd=str(ROOT),
        )
        client = ClaudeSDKClient(options=options)
        await client.connect()
        return cls(client, store)

    async def turn(self, user_text):
        await self.client.query(user_text)  # replaces: loop.py
        text_parts, tools, call_ids, result = [], [], [], None
        async for msg in self.client.receive_response():  # replaces: loop.py
            if isinstance(msg, SystemMessage) and msg.subtype == "init":
                print(f"  [SDK/agent.py] init: tools={msg.data.get('tools')}")
            elif isinstance(msg, AssistantMessage):
                if msg.message_id not in call_ids:
                    call_ids.append(msg.message_id)  # כמה הודעות יכולות להגיע מאותה קריאה למודל
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        tools.append(block.name.removeprefix(PREFIX))
                    elif hasattr(block, "text"):
                        text_parts.append(block.text)
            elif isinstance(msg, ResultMessage):
                result = msg

        usage = result.usage or {}  # replaces: tokens.py
        total = result.total_cost_usd or 0.0  # replaces: tokens.py
        cost, self.prev_cost = total - self.prev_cost, total
        self.session_id = result.session_id
        (Path(self.store.dir) / "sdk_session_id.txt").write_text(result.session_id, encoding="utf-8")  # replaces: history.py
        tokens = {
            "input": usage.get("input_tokens", 0),
            "cache_read": usage.get("cache_read_input_tokens", 0),
            "cache_write": usage.get("cache_creation_input_tokens", 0),
            "output": usage.get("output_tokens", 0),
        }
        print(f"  [SDK/agent.py] result: {tokens} ${cost:.4f} turns={result.num_turns}")
        return {
            "response": (result.result or "\n".join(text_parts)).strip(),
            "tokens": tokens,
            "model_calls": len(call_ids),
            "tools": tools,
            "cost_usd": cost,
        }

    async def close(self):
        await self.client.disconnect()
