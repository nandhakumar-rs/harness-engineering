# Step 2: Set up the OpenAI SDK

**Files:** `backend/.env`, `backend/app/agent.py`

## What to do

1. Install the SDK:
   ```bash
   cd backend
   uv add openai
   ```
2. Put your key in `backend/.env` (it's git-ignored, so never commit it):
   ```
   OPENAI_API_KEY=sk-...
   MODEL=gpt-4.1-mini
   MAX_ITERATIONS=6
   ```
3. In `agent.py`, create **one** async client at module level:
   ```python
   import os
   from openai import AsyncOpenAI

   client = AsyncOpenAI()          # reads OPENAI_API_KEY from the environment
   MODEL = os.getenv("MODEL", "gpt-4.1-mini")
   ```

`main.py` already calls `load_dotenv()` before it imports your agent, so the env vars are set by the time `AsyncOpenAI()` runs.

## Why async?
FastAPI streams the response while your loop is still running. An async client lets the server handle other requests while one is waiting on the model.

## We only use this one call
```python
await client.chat.completions.create(model=..., messages=..., tools=..., stream=True)
```
That's the whole SDK surface for this cohort.

## Check
```bash
uv run python -c "
import asyncio
from dotenv import load_dotenv; load_dotenv()
from openai import AsyncOpenAI
r = asyncio.run(AsyncOpenAI().chat.completions.create(
    model='gpt-4.1-mini', messages=[{'role':'user','content':'Say hi in 3 words'}]))
print(r.choices[0].message.content)"
```
