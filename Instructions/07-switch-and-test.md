# Step 7: Switch over and test

**File:** `backend/app/main.py`

## What to do

1. Flip the switch:
   ```python
   USE_FAKE_AGENT = False
   ```
2. Restart the backend (`--reload` usually picks it up). `GET /api/health` should now return `"agent": "openai"`.
3. Open http://localhost:3000 and try each ticket below.

## Test tickets

```
I was charged twice for my Pro subscription this month. Please refund the duplicate.
```
```
The export button does nothing in Safari. Chrome works fine.
```
```
We're a team of 50. What's your pricing and is there a volume discount?
```
```
I can't log in. The reset password email never arrives.
```

## What "done" looks like

- [ ] The chat shows **Thinking…** → `classifyTicket` → `searchKnowledgeBase` → `draftReply` → `sendReply`, each card turning **Completed**.
- [ ] Expanding a card shows the real arguments the model chose and the result your handler returned.
- [ ] The final answer **streams in** word by word.
- [ ] The Event stream shows `run.started`, one `iteration.started` per model call, the tool events, the `message.delta` events and `run.completed`.
- [ ] With `MAX_ITERATIONS=2` the run stops with `run.failed`.
- [ ] Your code uses only `client.chat.completions.create` from the SDK.

## Stretch goals
- Paste **three tickets in one message** ("item-1: … item-2: … item-3: …"). Does the model call tools in parallel? Count the iterations.
- Make `classifyTicket` take the category from the model (an enum argument) instead of hard-coding it.
- Try a cap of `3`. Which step does the model skip or fail on?
- Log the token usage of every call: pass `stream_options={"include_usage": True}` and read `chunk.usage` on the last chunk.

## Common errors

| Error | Cause |
|---|---|
| `messages with role 'tool' must be a response to a preceding message with 'tool_calls'` | You didn't append the assistant message (4.4) before the tool results. |
| `An assistant message with 'tool_calls' must be followed by tool messages…` | A `tool_call_id` didn't get its `tool` message. |
| `json.decoder.JSONDecodeError` on arguments | You parsed the arguments before the stream finished. Stitch first, parse after. |
| `TypeError: handler() got an unexpected keyword argument` | Your schema's property names don't match your Python parameter names. |
| `AuthenticationError` | `OPENAI_API_KEY` is missing in `backend/.env`, or the server wasn't restarted. |
