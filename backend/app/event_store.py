"""Records a run's events into event_log and announces each one on the bus.

    recorder = RunRecorder()
    async for e in run(...):
        yield to_sse(recorder.record(e))   # numbers + queues the event, returns it immediately
    recorder.finish()                      # writes whatever is still queued, then stops

Every event except message.delta is stored, with a seq numbered 1, 2, 3...
within its run. Writing and notifying is ONE statement:

    INSERT ... ON CONFLICT (run_id, seq) DO NOTHING   -- a repeated event is skipped
    then pg_notify(...) only for a row that was really inserted

Writes happen in a background task, one at a time and in order, so a slow
database round trip never holds up the live stream to the browser.
"""

import asyncio
import json
import logging

import psycopg

from .bus import CHANNEL, notify_payload
from .db import DATABASE_URL
from .events import Event

log = logging.getLogger("harness.event_store")

LIVE_ONLY = {"message.delta"}  # too many, too small, and different on every retry

INSERT_AND_NOTIFY = """
WITH inserted AS (
  INSERT INTO event_log (run_id, seq, type, data, created_at)
  VALUES (%(run_id)s, %(seq)s, %(type)s, %(data)s, to_timestamp(%(ts)s / 1000.0))
  ON CONFLICT (run_id, seq) DO NOTHING
  RETURNING 1
)
SELECT pg_notify(%(channel)s, %(payload)s) FROM inserted
"""

_conn: psycopg.AsyncConnection | None = None
_conn_lock = asyncio.Lock()
_writers: set[asyncio.Task] = set()  # keep running writers referenced until they finish


async def _connection() -> psycopg.AsyncConnection:
    """One shared autocommit connection for all writes (each INSERT commits on its own)."""
    global _conn
    async with _conn_lock:
        if _conn is None or _conn.closed:
            _conn = await psycopg.AsyncConnection.connect(DATABASE_URL, autocommit=True)
    return _conn


async def start() -> None:
    await _connection()  # open it at startup so the first write doesn't pay the connection cost


async def stop() -> None:
    global _conn
    if _writers:
        await asyncio.gather(*_writers, return_exceptions=True)
    if _conn:
        await _conn.close()
        _conn = None


class RunRecorder:
    def __init__(self) -> None:
        self.run_id: str | None = None
        self.seq = 0
        self._queue: asyncio.Queue[Event | None] = asyncio.Queue()
        task = asyncio.create_task(self._write_all())
        _writers.add(task)
        task.add_done_callback(_writers.discard)

    def record(self, e: Event) -> Event:
        if e.type == "run.started":
            self.run_id = e.data["runId"]
        if self.run_id is None or e.type in LIVE_ONLY:
            return e
        self.seq += 1
        e.seq = self.seq
        self._queue.put_nowait(e)
        return e

    def finish(self) -> None:
        self._queue.put_nowait(None)  # the writer stops after flushing everything before this

    async def _write_all(self) -> None:
        while (e := await self._queue.get()) is not None:
            try:
                conn = await _connection()
                await conn.execute(INSERT_AND_NOTIFY, {
                    "run_id": self.run_id,
                    "seq": e.seq,
                    "type": e.type,
                    "data": json.dumps(e.data),
                    "ts": e.ts,
                    "channel": CHANNEL,
                    "payload": notify_payload(self.run_id, e.model_dump()),
                })
            except Exception as exc:  # never break the live stream because the log is unavailable
                log.warning("could not store %s seq=%s for run %s: %s", e.type, e.seq, self.run_id, exc)
