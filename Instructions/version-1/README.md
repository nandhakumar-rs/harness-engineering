# Session 1: Tool calls

By the end of this session the fake agent is gone. In its place is a real agent loop that you wrote by hand. It reads a support ticket, calls four tools, streams its answer, and shows every step in both panels of the UI.

## Rules for this cohort

1. The OpenAI SDK is used **only** to call the model and to pass tool definitions.
2. **No** Agents SDK, no built-in runners, hooks or tool helpers (`openai-agents`, `client.beta.*.run_tools`, `@function_tool`…).
3. The loop, the iteration cap and the events are code **you** write.

The point is to see exactly what a "harness" does around a model. If a library hides the loop, there's nothing left to learn.

## Steps

Do them in order. Each step ends with a **Check** you can run before moving on.

| # | Step | File(s) you touch |
|---|---|---|
| 1 | [Build the knowledge base](01-knowledge-base.md) | `backend/app/knowledge_base.py` |
| 2 | [Set up the OpenAI SDK](02-openai-setup.md) | `backend/.env`, `backend/app/agent.py` |
| 3 | [Register the four tools](03-register-tools.md) | `backend/app/tools.py` |
| 4 | [Write the agent loop](04-agent-loop.md) | `backend/app/agent.py` |
| 5 | [Cap the loop yourself](05-max-iterations.md) | `backend/app/agent.py`, `.env` |
| 6 | [Show the thinking status](06-thinking-status.md) | `backend/app/agent.py` |
| 7 | [Switch over and test](07-switch-and-test.md) | `backend/app/main.py` |

## Before you start

```bash
git checkout version-1
# backend
cd backend && cp .env.example .env && uv sync && uv run uvicorn app.main:app --reload
# frontend (new terminal)
cd frontend && pnpm install && pnpm dev
```

Open http://localhost:3000, send any message, and watch the **fake** run. Read `backend/app/fake_agent.py`. Your real agent has to emit the **same events in the same order**.

## The events you'll emit

```python
from .events import event

event("run.started", runId=run_id)
event("iteration.started", iteration=i, max=max_iterations)
event("thinking", status="started")          # or "stopped"
event("message.delta", text="Hello")
event("tool.requested", toolCallId=id, name=name, args=args)
event("tool.completed", toolCallId=id, result=result)
event("tool.failed", toolCallId=id, error="...")
event("run.completed", runId=run_id, iterations=i)
event("run.failed", runId=run_id, error="...")
```

`run_agent` is an **async generator**: you `yield` events and `main.py` turns each one into an SSE message for the UI.
