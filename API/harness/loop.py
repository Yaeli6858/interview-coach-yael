"""לולאת הסוכן: קוראים למודל כל עוד stop_reason == "tool_use".

בכל סבב: בונים בקשה -> קוראים למודל -> אם ביקש כלים, מריצים את כולם
ומחזירים את כל ה-tool_result בהודעת user אחת -> שוב למודל.
"""
from . import block_to_dict, log

MAX_ITERATIONS = 10  # הגנה מלולאה אינסופית


def run(client, build_request, messages, toolbox, history, usage):
    tools_called = []
    for i in range(1, MAX_ITERATIONS + 1):
        response = client.messages.create(**build_request())
        usage.add(response.usage)
        log(__file__, f"call #{i}: stop_reason={response.stop_reason}")

        assistant = {"role": "assistant", "content": [block_to_dict(b) for b in response.content]}
        messages.append(assistant)
        history.append(assistant)

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            return text, tools_called

        results = []
        for block in response.content:
            if block.type == "tool_use":
                tools_called.append(block.name)
                results.append(toolbox.execute(block.id, block.name, block.input))
        tool_message = {"role": "user", "content": results}  # כל התוצאות בהודעה אחת
        messages.append(tool_message)
        history.append(tool_message)
        log(__file__, f"sent {len(results)} tool_result(s) in one message")

    log(__file__, f"stopped after {MAX_ITERATIONS} iterations")
    return "(הסוכן עצר: יותר מדי סבבי כלים)", tools_called
