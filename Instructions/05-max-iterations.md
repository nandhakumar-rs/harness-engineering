# Step 5: Cap the loop yourself

**File:** `backend/app/agent.py` (`MAX_ITERATIONS` is set in `.env`)

A model can keep calling tools forever: it retries, it loops, or it misreads a result. Every harness needs a hard stop, and in this cohort **you** write it. No SDK `max_turns`.

## What to do

1. Replace `while True:` with a counted loop:
   ```python
   for iteration in range(1, max_iterations + 1):
       yield event("iteration.started", iteration=iteration, max=max_iterations)
       ...   # 4.2 - 4.6
   ```
2. If the loop **finishes without returning**, the cap was hit:
   ```python
   yield event("run.failed", runId=run_id, error=f"max_iterations ({max_iterations}) reached")
   ```
3. `main.py` already reads `MAX_ITERATIONS` from `.env` and passes it in as `max_iterations`.

## What is "one iteration"?
**One model call.** A single model response can request several tools at once. That's still one iteration.

## Check
1. Set `MAX_ITERATIONS=2` in `.env` and restart the backend.
2. Send a ticket. You should see `iteration.started {"iteration":2,"max":2}`, then a red `run.failed` card in the chat.
3. Set it back to `6`.

## Think about
- How many iterations does a normal ticket need? (Usually 5: four tool steps plus the final answer.) What's a sensible cap?
- What should the *user* see when the cap is hit? Right now it's an error card. Later sessions handle this more gracefully.
