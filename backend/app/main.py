from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from . import bus, event_store, runs  # noqa: E402
from .db import init_db  # noqa: E402
from .events import to_sse  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()  # create event_log if needed; fails fast if the database is unreachable
    await bus.start()  # LISTEN for live events
    await event_store.start()
    yield
    await event_store.stop()  # flush pending writes first
    await bus.stop()


app = FastAPI(title="Harness Inspector API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class StartRun(BaseModel):
    # The client picks the id, so sending the same request twice can't start two runs.
    runId: str = Field(pattern=r"^[A-Za-z0-9_-]{4,64}$")
    messages: list[ChatMessage]


@app.get("/api/health")
def health():
    return {"ok": True, "agent": "fake" if runs.USE_FAKE_AGENT else "openai"}


@app.post("/api/runs")
async def start_run(req: StartRun):
    started = await runs.start_run(req.runId, [m.model_dump() for m in req.messages])
    return {"runId": req.runId, "started": started}


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str, after: int = 0):
    """SSE: everything after `after` from event_log (catch-up), then live events from the bus."""

    async def stream():
        async for e in runs.watch_run(run_id, after):
            yield to_sse(e)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
