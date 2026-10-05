"""The agent loop, written by hand.

Rules for this cohort: the OpenAI SDK is ONLY used to call the model and pass
tool definitions. No built-in agents, runners or hooks — the loop is yours.

    messages = [system, ...conversation]
    loop:
        response = model(messages, tools)          # streamed
        no tool calls?  -> done
        for each tool call: run it, append the result to messages

Still TODO: Step 5 (cap the loop at max_iterations), Step 6 (thinking events).
"""

import json
import os
import uuid
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from .events import Event, event
from .tools import TOOLS, dispatch

client = AsyncOpenAI()  # reads OPENAI_API_KEY from the environment
MODEL = os.getenv("MODEL", "gpt-4.1-mini")

SYSTEM_PROMPT = """You are a customer support agent.
For every ticket:
1. classifyTicket
2. searchKnowledgeBase with the category
3. draftReply using what you found
4. sendReply with the draftId
Then summarise what you did in one or two sentences."""


async def run_agent(messages: list[dict], max_iterations: int = 6) -> AsyncIterator[Event]:
    run_id = uuid.uuid4().hex[:8]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    yield event("run.started", runId=run_id)

    iteration = 0
    while True:  # Step 5 replaces this with a bounded loop
        iteration += 1
        yield event("iteration.started", iteration=iteration, max=max_iterations)

        # 4.2 Call the model, streaming
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            stream=True,
        )

        # 4.3 Read the stream: text goes straight to the UI,
        # tool calls arrive in fragments and are stitched together by index
        text = ""
        calls: dict[int, dict[str, str]] = {}
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                text += delta.content
                yield event("message.delta", text=delta.content)

            for tc in delta.tool_calls or []:
                call = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    call["id"] = tc.id
                if tc.function and tc.function.name:
                    call["name"] += tc.function.name
                if tc.function and tc.function.arguments:
                    call["arguments"] += tc.function.arguments

        # 4.4 Remember what the model said, including the tool calls it asked for
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": text or None}
        if calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": c["id"],
                    "type": "function",
                    "function": {"name": c["name"], "arguments": c["arguments"]},
                }
                for c in calls.values()
            ]
        messages.append(assistant_msg)

        # 4.5 No tool calls? The model has answered — done.
        if not calls:
            yield event("run.completed", runId=run_id, iterations=iteration)
            return

        # 4.6 Run every tool call and send each result back to the model
        for c in calls.values():
            args = json.loads(c["arguments"] or "{}")
            yield event("tool.requested", toolCallId=c["id"], name=c["name"], args=args)

            result = dispatch(c["name"], args)
            yield event("tool.completed", toolCallId=c["id"], result=result)

            messages.append({
                "role": "tool",
                "tool_call_id": c["id"],
                "content": json.dumps(result),
            })
