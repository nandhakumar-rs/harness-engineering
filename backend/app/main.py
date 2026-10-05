import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .events import event, to_sse

load_dotenv()

# Session 1: flip this to False once app/agent.py is implemented.
USE_FAKE_AGENT = False

if USE_FAKE_AGENT:
    from .fake_agent import run_fake_agent as run
else:
    from .agent import run_agent as run

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "6"))

app = FastAPI(title="Harness Inspector API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@app.get("/api/health")
def health():
    return {"ok": True, "agent": "fake" if USE_FAKE_AGENT else "openai"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    messages = [m.model_dump() for m in req.messages]

    async def stream():
        try:
            async for e in run(messages, max_iterations=MAX_ITERATIONS):
                yield to_sse(e)
        except Exception as exc:  # surface errors in the event stream instead of dropping the connection
            yield to_sse(event("run.failed", error=f"{type(exc).__name__}: {exc}"))

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
