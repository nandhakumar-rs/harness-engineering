# Step 6: Show the thinking status

**File:** `backend/app/agent.py`

There's a gap between sending a request and receiving the first token. The UI shows **"Thinking…"** during that gap so the user knows something is happening.

## What to do

1. Emit `thinking: started` just **before** each model call.
2. Emit `thinking: stopped` when the **first chunk** arrives, only once per iteration.
3. Also emit `stopped` if the stream ends without any chunks, so the indicator never gets stuck.

```python
yield event("thinking", status="started")
stream = await client.chat.completions.create(...)

thinking = True
async for chunk in stream:
    if thinking:
        thinking = False
        yield event("thinking", status="stopped")
    ...

if thinking:
    yield event("thinking", status="stopped")
```

## Check
In the UI you should see **Thinking…** before each tool card appears, and in the Event stream panel you should see a `thinking` started/stopped pair for each iteration.
