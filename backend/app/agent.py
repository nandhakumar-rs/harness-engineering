"""Session 1 — TODO: the agent loop, written by hand.

Rules for this cohort: the OpenAI SDK is ONLY used to call the model and pass
tool definitions. No built-in agents, runners or hooks — the loop is yours.

Outline:

    client = AsyncOpenAI()                       # reads OPENAI_API_KEY
    yield event("run.started", runId=...)
    for iteration in range(1, max_iterations + 1):
        yield event("iteration.started", iteration=iteration, max=max_iterations)
        yield event("thinking", status="started")
        stream = await client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, stream=True
        )
        # for each chunk:
        #   - text delta      -> yield event("message.delta", text=...)
        #   - tool_call delta -> accumulate id / name / arguments by index
        yield event("thinking", status="stopped")    # once the first token arrives
        # append the assistant message (with its tool_calls) to messages
        # no tool calls?  -> yield event("run.completed", ...) and return
        # for each tool call:
        #   yield event("tool.requested", toolCallId=..., name=..., args=...)
        #   result = dispatch(name, args)
        #   yield event("tool.completed", toolCallId=..., result=result)
        #   messages.append({"role": "tool", "tool_call_id": ..., "content": json.dumps(result)})
    # loop ran out -> yield event("run.failed", error="max_iterations reached")
"""

import os
from typing import AsyncIterator

from openai import AsyncOpenAI

from .events import Event

client = AsyncOpenAI()  # reads OPENAI_API_KEY from the environment
MODEL = os.getenv("MODEL", "gpt-4.1-mini")


async def run_agent(messages: list[dict], max_iterations: int = 6) -> AsyncIterator[Event]:
    raise NotImplementedError("Session 1: implement the agent loop")
    yield  # makes this an async generator
