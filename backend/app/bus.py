"""The event bus: live notifications over Postgres LISTEN/NOTIFY.

event_log is the history (durable, replayable). The bus is the doorbell:
"run X just produced an event". It's live-only and fine to lose, because a
reconnecting browser catches up from event_log.

    publish(run_id, event)          -> NOTIFY on the harness_events channel
    async with subscribe(run_id) as queue:
        event = await queue.get()   -> events for that run, as they happen

One dedicated connection LISTENs for the whole process and fans each
notification out to the in-memory queues of that run's subscribers.
Needs Neon's direct host: LISTEN doesn't work through the "-pooler" host.
"""

import asyncio
import json
import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import psycopg

from .db import DATABASE_URL

log = logging.getLogger("harness.bus")

CHANNEL = "harness_events"
MAX_PAYLOAD = 7900  # Postgres caps a NOTIFY payload at 8000 bytes

_subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
_publisher: psycopg.AsyncConnection | None = None
_listener_task: asyncio.Task | None = None


async def publish(run_id: str, event: dict[str, Any], conn: psycopg.AsyncConnection | None = None) -> None:
    """Announce an event for a run.

    Pass `conn` to send the NOTIFY inside your own transaction: Postgres then
    delivers it only when that transaction commits.
    """
    payload = notify_payload(run_id, event)
    await (conn or await _publisher_conn()).execute("SELECT pg_notify(%s, %s)", (CHANNEL, payload))


def notify_payload(run_id: str, event: dict[str, Any]) -> str:
    """The NOTIFY message for an event, or a pointer to its event_log row if it's too big."""
    payload = json.dumps({"runId": run_id, "event": event})
    if len(payload.encode()) > MAX_PAYLOAD:
        payload = json.dumps({"runId": run_id, "ref": {"seq": event.get("seq"), "type": event.get("type")}})
    return payload


@asynccontextmanager
async def subscribe(run_id: str) -> AsyncIterator[asyncio.Queue]:
    """Receive every event published for `run_id` while the block is open."""
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers[run_id].add(queue)
    try:
        yield queue
    finally:
        _subscribers[run_id].discard(queue)
        if not _subscribers[run_id]:
            del _subscribers[run_id]


async def start() -> None:
    """Start the background listener. Call once at app startup."""
    global _listener_task
    ready = asyncio.Event()
    _listener_task = asyncio.create_task(_listen(ready))
    await asyncio.wait_for(ready.wait(), timeout=15)
    await _publisher_conn()  # open it now so the first publish doesn't pay the connection cost


async def stop() -> None:
    global _listener_task, _publisher
    if _listener_task:
        _listener_task.cancel()
        _listener_task = None
    if _publisher:
        await _publisher.close()
        _publisher = None


async def _publisher_conn() -> psycopg.AsyncConnection:
    global _publisher
    if _publisher is None or _publisher.closed:
        _publisher = await psycopg.AsyncConnection.connect(DATABASE_URL, autocommit=True)
    return _publisher


async def _listen(ready: asyncio.Event) -> None:
    """LISTEN forever, reconnecting if the connection drops (e.g. Neon suspends when idle)."""
    while True:
        try:
            async with await psycopg.AsyncConnection.connect(DATABASE_URL, autocommit=True) as conn:
                await conn.execute(f"LISTEN {CHANNEL}")
                ready.set()
                async for note in conn.notifies():
                    message = json.loads(note.payload)
                    for queue in _subscribers.get(message["runId"], ()):
                        queue.put_nowait(message.get("event") or {"ref": message["ref"]})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("event bus listener lost its connection (%s); reconnecting", exc)
            await asyncio.sleep(1)
