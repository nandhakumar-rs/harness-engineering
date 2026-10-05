"""The event protocol shared by the backend and the UI.

Every event the harness emits has the same shape: { id, ts, type, data, seq }.
seq is set when the event is stored in event_log (message.delta never is).
The frontend mirrors these types in frontend/lib/events.ts.
"""

import json
import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "run.started",
    "run.completed",
    "run.failed",
    "iteration.started",
    "thinking",
    "message.delta",
    "message.completed",
    "tool.requested",
    "tool.completed",
    "tool.failed",
]


class Event(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    ts: float = Field(default_factory=lambda: time.time() * 1000)
    type: EventType
    data: dict[str, Any] = Field(default_factory=dict)
    seq: int | None = None  # position in event_log; None for live-only events


def event(type: EventType, **data: Any) -> Event:
    """Shorthand: event("tool.requested", toolCallId=..., name=..., args=...)"""
    return Event(type=type, data=data)


def to_sse(e: Event) -> str:
    """Serialize one event as a Server-Sent Events message.

    Stored events also get an `id:` line (their seq), the SSE convention for
    "where was I?" when a client reconnects.
    """
    id_line = f"id: {e.seq}\n" if e.seq is not None else ""
    return f"{id_line}data: {json.dumps(e.model_dump())}\n\n"
