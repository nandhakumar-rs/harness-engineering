"""The agent loop, written by hand, as a durable DBOS workflow.

Rules for this cohort: the OpenAI SDK is ONLY used to call the model and pass
tool definitions. No built-in agents, runners or hooks — the loop is yours.

    messages = [system, ...conversation]
    loop:
        response = call_model(messages, tools)     # STEP: output saved by DBOS
        no tool calls?  -> done
        for each tool call: run_tool(...)          # STEP: output saved by DBOS
    ran out of iterations? -> run.failed

Durability (Session 2):
- The loop is a @DBOS.workflow. Each model call and each tool call is a
  @DBOS.step, so its output is saved in DBOS's own tables when it finishes.
- After a crash, DBOS runs the workflow again from the top. Finished steps
  return their saved output instead of running (no repeated OpenAI calls, no
  repeated tools); the first unfinished step really runs.
- Because the body runs again, it must make the same choices every time: no
  random/time/uuid decisions here. Stored events are emitted from the body with
  a counter (seq 1, 2, 3...), so replayed events get the same seq and event_log
  skips them (ON CONFLICT DO NOTHING).
- Inside a step, only live-only events (message.delta) may be emitted: a step
  doesn't run again on recovery, so anything stored from inside it would shift
  the numbering.
"""

import json
import os
import time
from typing import Any

from dbos import DBOS
from dbos._error import DBOSException, DBOSMaxStepRetriesExceeded
from openai import AsyncOpenAI

from . import event_store
from .events import event
from .tools import TOOLS, dispatch

MODEL = os.getenv("MODEL", "gpt-4.1-mini")

SYSTEM_PROMPT = """You are a customer support agent.
If the message is a greeting, small talk, or doesn't describe a support issue,
reply briefly and ask how you can help. Do not call any tools.

If it is a support ticket:
1. classifyTicket
2. searchKnowledgeBase with the category
3. draftReply using what you found
4. sendReply with the draftId
Then summarise what you did in one or two sentences."""


@DBOS.step(retries_allowed=True, max_attempts=3, interval_seconds=1.0)
async def call_model(run_id: str, messages: list[dict]) -> dict[str, Any]:
    """One streamed model call. Text goes out live; the full reply is the step's saved output."""
    # A client per call: after a crash DBOS may resume this on a different event loop,
    # and an HTTP client can't be shared across loops.
    async with AsyncOpenAI() as client:
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            stream=True,
        )

        text = ""
        calls: dict[int, dict[str, str]] = {}
        first_chunk_ts: float | None = None
        async for chunk in stream:
            if first_chunk_ts is None:
                first_chunk_ts = time.time() * 1000
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                text += delta.content
                event_store.record(run_id, event("message.delta", text=delta.content))  # live-only

            for tc in delta.tool_calls or []:
                call = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    call["id"] = tc.id
                if tc.function and tc.function.name:
                    call["name"] += tc.function.name
                if tc.function and tc.function.arguments:
                    call["arguments"] += tc.function.arguments

    return {"text": text, "tool_calls": list(calls.values()), "first_chunk_ts": first_chunk_ts}


@DBOS.step()
async def run_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return dispatch(name, args)


@DBOS.workflow()
async def agent_workflow(run_id: str, messages: list[dict], max_iterations: int = 6) -> None:
    seq = 0

    def emit(type_: str, ts: float | None = None, **data: Any) -> None:
        """Store an event under the next seq. Same code, same order -> same seq on recovery."""
        nonlocal seq
        seq += 1
        e = event(type_, **data)
        e.seq = seq
        if ts:
            e.ts = ts
        event_store.record(run_id, e)

    try:
        user_input = messages[-1]["content"] if messages else ""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
        emit("run.started", runId=run_id, input=user_input)

        # One iteration = one model call. The cap is ours, not the SDK's.
        for iteration in range(1, max_iterations + 1):
            emit("iteration.started", iteration=iteration, max=max_iterations)

            emit("thinking", status="started")
            reply = await call_model(run_id, messages)
            emit("thinking", status="stopped", ts=reply["first_chunk_ts"])

            # The deltas were live-only; the full text is stored once.
            if reply["text"]:
                emit("message.completed", text=reply["text"])

            assistant_msg: dict[str, Any] = {"role": "assistant", "content": reply["text"] or None}
            if reply["tool_calls"]:
                assistant_msg["tool_calls"] = [
                    {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                    for c in reply["tool_calls"]
                ]
            messages.append(assistant_msg)

            if not reply["tool_calls"]:
                emit("run.completed", runId=run_id, iterations=iteration)
                return

            for c in reply["tool_calls"]:
                args = json.loads(c["arguments"] or "{}")
                emit("tool.requested", toolCallId=c["id"], name=c["name"], args=args)
                result = await run_tool(c["name"], args)
                emit("tool.completed", toolCallId=c["id"], result=result)
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(result)})

        # The loop ran out without the model finishing: the cap was hit.
        emit("run.failed", runId=run_id, error=f"max_iterations ({max_iterations}) reached")
    except Exception as exc:
        # DBOS uses exceptions to control the workflow itself (cancelled, owned by another
        # process, nondeterminism detected): let those through. Anything else is a failed run.
        if isinstance(exc, DBOSException) and not isinstance(exc, DBOSMaxStepRetriesExceeded):
            raise
        emit("run.failed", runId=run_id, error=f"{type(exc).__name__}: {exc}")
    finally:
        event_store.finish(run_id)
