"""The agent loop, written by hand.

Rules for this cohort: the OpenAI SDK is ONLY used to call the model and pass
tool definitions. No built-in agents, runners or hooks — the loop is yours.

The whole idea, in six lines:

    messages = [system, ...conversation]
    loop up to max_iterations times:
        response = model(messages, tools)      # streaming
        append the response to messages        # including its tool_calls
        if it asked for no tools: done
        for each tool it asked for:
            run it, append the result to messages

One iteration is ONE model call. A single response may request several tools;
that is still one iteration.
"""

import json
import os
import uuid
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from .events import Event, event
from .tools import TOOLS, dispatch

# One client for the whole process. AsyncOpenAI() reads OPENAI_API_KEY from the
# environment; main.py calls load_dotenv() before importing this module.
client = AsyncOpenAI()

MODEL = os.getenv("MODEL", "gpt-4.1-mini")

# The system prompt is part of the harness. The "do not call any tools" path
# matters: without it the model treats "Hi" as a ticket, and because `category`
# is an enum with no "none of these" option it must pick one — so it emails a
# billing reply to someone who only said hello.
SYSTEM_PROMPT = """You are a customer support agent.

If the message is a greeting, small talk, or does not describe a support issue,
reply briefly and ask how you can help. Do not call any tools.

If it is a support ticket, work through the tools in this order:
1. classifyTicket
2. searchKnowledgeBase with the category it returned
3. draftReply, grounded in the articles you found — quote their specifics
4. sendReply with the draftId that draftReply returned

Then summarise what you did in one or two sentences."""


async def run_agent(messages: list[dict], max_iterations: int = 6) -> AsyncIterator[Event]:
    run_id = uuid.uuid4().hex[:8]

    # A new list, so the caller's messages are never mutated.
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]

    yield event("run.started", runId=run_id)

    for iteration in range(1, max_iterations + 1):
        yield event("iteration.started", iteration=iteration, max=max_iterations)

        # Emitted BEFORE the call: create() itself is a network round trip, and
        # the wait for the first token is the gap the indicator covers.
        yield event("thinking", status="started")
        thinking = True

        stream = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            stream=True,
        )

        text = ""
        calls: dict[int, dict[str, str]] = {}  # index -> {id, name, arguments}

        async for chunk in stream:
            # First sign of life ends the wait — once per iteration only.
            if thinking:
                thinking = False
                yield event("thinking", status="stopped")

            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                text += delta.content
                yield event("message.delta", text=delta.content)

            # Tool calls arrive in fragments. Only the first fragment for an
            # index carries id and name; the rest carry slices of the arguments
            # JSON string. Stitch by index now, parse once the stream is done.
            for tc in delta.tool_calls or []:
                call = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    call["id"] = tc.id
                if tc.function and tc.function.name:
                    call["name"] += tc.function.name
                if tc.function and tc.function.arguments:
                    call["arguments"] += tc.function.arguments

        # An empty stream would otherwise leave the indicator spinning forever.
        if thinking:
            thinking = False
            yield event("thinking", status="stopped")

        # Record what the model said BEFORE any tool result. The API rejects a
        # `tool` message that does not follow an assistant message with tool_calls.
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

        # The model answered without asking for anything. That is what ends a run.
        if not calls:
            yield event("run.completed", runId=run_id, iterations=iteration)
            return

        # Run every requested call. Each tool_call_id MUST get exactly one `tool`
        # message back, or the next model call fails — so every branch below
        # appends one, including the failures.
        for c in calls.values():
            call_id = c["id"]

            try:
                args = json.loads(c["arguments"] or "{}")
            except json.JSONDecodeError as exc:
                yield event("tool.requested", toolCallId=call_id, name=c["name"], args=c["arguments"])
                yield event("tool.failed", toolCallId=call_id, error=f"invalid JSON arguments: {exc}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps({"ok": False, "error": "arguments were not valid JSON"}),
                })
                continue

            yield event("tool.requested", toolCallId=call_id, name=c["name"], args=args)

            try:
                result = dispatch(c["name"], args)
            except Exception as exc:
                # A hallucinated tool name or a bad argument must not kill the
                # run: report it and let the model read the error and recover.
                error = f"{type(exc).__name__}: {exc}"
                yield event("tool.failed", toolCallId=call_id, error=error)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps({"ok": False, "error": error}),
                })
                continue

            yield event("tool.completed", toolCallId=call_id, result=result)
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(result),
            })

    # Fell out of the loop without returning: the cap was hit.
    yield event("run.failed", runId=run_id, error=f"max_iterations ({max_iterations}) reached")
