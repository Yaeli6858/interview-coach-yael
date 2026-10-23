"""הכלים בגרסת ה-SDK: אותם כלים מ-shared/, עטופים ב-@tool ומוגשים כשרת MCP בתוך התהליך."""
from claude_agent_sdk import create_sdk_mcp_server, tool

from shared.domain import TOOL_SPECS, ToolError, run_tool

SERVER_NAME = "coach"
ALLOWED_TOOLS = [f"mcp__{SERVER_NAME}__{s['name']}" for s in TOOL_SPECS]  # replaces: tools.py


def _wrap(store, spec):
    @tool(spec["name"], spec["description"], spec["input_schema"])  # replaces: tools.py
    async def handler(args):
        try:
            text = run_tool(store, spec["name"], args)  # replaces: tools.py
            print(f"  [SDK/tools.py] {spec['name']}({args}) -> {len(text)} chars")
            return {"content": [{"type": "text", "text": text}]}
        except ToolError as e:
            print(f"  [SDK/tools.py] {spec['name']}({args}) -> is_error: {e}")
            return {"content": [{"type": "text", "text": str(e)}], "is_error": True}  # replaces: tools.py
    return handler


def build_server(store):
    return create_sdk_mcp_server(  # replaces: tools.py
        name=SERVER_NAME, version="1.0.0", tools=[_wrap(store, s) for s in TOOL_SPECS])
