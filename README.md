# Harness Engineering: Customer Support Harness

Over this cohort you'll build a **customer support harness**: an LLM agent that reads a support ticket, classifies it, looks up answers, drafts a reply and sends it. Every step is visible in a live event stream.

Each session has its own branch. `version-1` is the starting point for **Session 1: Tool calls**.

```
┌──────────────────────────────┬──────────────────────────────┐
│ Agent (chat)                 │ Event stream                 │
│  user message                │ 11:28:34 run.started   {…}   │
│  ✓ classifyTicket  Completed │ 11:28:34 tool.requested{…}   │
│  ✓ draftReply      Completed │ 11:28:34 tool.completed{…}   │
│  streamed answer…            │ 11:28:35 message.delta {…}   │
└──────────────────────────────┴──────────────────────────────┘
```

## Stack

| Part | Tech |
|---|---|
| UI | Next.js (App Router) + shadcn/ui + Tailwind (`frontend/`) |
| API | FastAPI, streaming Server-Sent Events (`backend/`) |
| LLM | `openai` Python SDK, **added by you in Session 1** |

## Run it

Prerequisites: Node 20+, [pnpm](https://pnpm.io), [uv](https://docs.astral.sh/uv/).

```bash
# Terminal 1: backend on http://localhost:8000
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload

# Terminal 2: frontend on http://localhost:3000
cd frontend
pnpm install
pnpm dev
```

Open http://localhost:3000. The header should say **connected**. Send any message and you'll see a **scripted fake run** (`backend/app/fake_agent.py`): thinking, four tool calls and a streamed answer. No model is involved yet. The UI already understands every event your real agent will emit.

## How it fits together

```
frontend/lib/use-agent-stream.ts ──POST /api/chat──▶ backend/app/main.py
          ▲                                               │
          │      text/event-stream (one event per line)   ▼
          └───────────────────────────────── run(messages, max_iterations)
                                               fake_agent.py  → today
                                               agent.py       → you build this
```

### The event protocol

Every event is `{ id, ts, type, data }` (`backend/app/events.py`, mirrored in `frontend/lib/events.ts`).

| type | data | UI |
|---|---|---|
| `run.started` / `run.completed` / `run.failed` | `{ runId, iterations?, error? }` | log, plus an error card on failure |
| `iteration.started` | `{ iteration, max }` | log |
| `thinking` | `{ status: "started" \| "stopped" }` | "Thinking…" indicator |
| `message.delta` | `{ text }` | streamed assistant text |
| `tool.requested` | `{ toolCallId, name, args }` | tool card → Running |
| `tool.completed` / `tool.failed` | `{ toolCallId, result \| error }` | tool card → Completed / Failed |

Emit these from `agent.py` with `event("tool.requested", toolCallId=..., name=..., args=...)` and the UI updates by itself. You don't need to touch the frontend in Session 1.

---

## Session 1: Tool calls

**Rule for this cohort:** the OpenAI SDK is used **only** to call the model and pass tool definitions. No Agents SDK, no built-in runners, hooks or tool helpers. You write the loop.

📘 **Step-by-step guide:** [`Instructions/version-1/`](Instructions/version-1/README.md), with one file per step, code hints and a check at the end of each.

### Tasks

- [ ] **1. Knowledge base** (`backend/app/knowledge_base.py`)
  Build a static key/value dict keyed by category (`billing`, `bug`, `sales`, `account`), with a few short articles each.

- [ ] **2. Set up the OpenAI SDK**
  `cd backend && uv add openai`, put your `OPENAI_API_KEY` in `.env`, and create an `AsyncOpenAI()` client in `agent.py`.

- [ ] **3. Register four tools** (`backend/app/tools.py`)
  Write JSON-schema definitions plus a Python handler for each, and a `dispatch(name, args)` function.
  | tool | returns |
  |---|---|
  | `classifyTicket(message)` | `{ ok: true, category }` |
  | `searchKnowledgeBase(category, query)` | `{ ok: true, articles }` from your KB |
  | `draftReply(message)` | `{ ok: true, draftId }` |
  | `sendReply(draftId)` | `{ ok: true, sentId }` |

  Every tool just returns success for now. Validation and a real email service come in later sessions.

- [ ] **4. Write the agent loop** (`backend/app/agent.py`)
  - Add a system prompt that tells the model it's a support agent and which tools to use, in what order.
  - Call `client.chat.completions.create(..., tools=TOOLS, stream=True)`.
  - Stream text chunks out as `message.delta`. Accumulate tool-call deltas by `index` (`id`, `function.name`, `function.arguments`).
  - Append the assistant message with its `tool_calls`. For each call, emit `tool.requested`, run `dispatch`, emit `tool.completed`, then append a `{"role": "tool", "tool_call_id": ..., "content": ...}` message.
  - Loop until the model answers with no tool calls → `run.completed`.

- [ ] **5. Cap the loop yourself**
  Count iterations and stop at `MAX_ITERATIONS` (from `.env`). Emit `run.failed` with `"max_iterations reached"`. Test it by setting `MAX_ITERATIONS=2`.

- [ ] **6. Thinking status**
  Emit `thinking` `started` before each model call and `stopped` when the first chunk arrives.

- [ ] **7. Switch over**
  In `backend/app/main.py`, set `USE_FAKE_AGENT = False`. Paste a ticket and watch both panels.

### Try these tickets

```
I was charged twice for my Pro subscription this month. Please refund the duplicate.
```
```
The export button does nothing in Safari. Chrome works fine.
```
```
We're a team of 50. What's your pricing and is there a volume discount?
```

## Roadmap

| Branch | Session |
|---|---|
| `version-1` | Tool calls: manual agent loop, streaming, events |
| `version-2` | … coming next |
