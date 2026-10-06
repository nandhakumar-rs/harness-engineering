"""Records a run's events into event_log and announces each one on the bus.

    record(run_id, e)   # queues the event, returns immediately; safe from any thread
    finish(run_id)      # writes whatever is still queued for that run, then stops

Every event except message.delta is stored under the seq the workflow gave it. Writing and notifying is ONE statement:

    INSERT ... ON CONFLICT (run_id, seq) DO NOTHING   -- a repeated event is skipped
    then pg_notify(...) only for a row that was really inserted

message.delta is live-only: it's announced on the bus but never stored.

Writes happen in a background task, in order. Everything waiting in the queue
is sent in one pipeline (one network round trip), and consecutive deltas are
merged into one, so a slow database never makes the live view fall behind.
"""

import asyncio
import json
import logging
from typing import Any

import psycopg

from .bus import CHANNEL, notify_payload
from .db import DATABASE_URL
from .events import Event

log = logging.getLogger("harness.event_store")

LIVE_ONLY = {"message.delta"}  # too many, too small, and different on every retry
MAX_MERGED_DELTA = 3000  # characters; keeps a merged delta well under the NOTIFY limit

INSERT_AND_NOTIFY = """
WITH inserted AS (
  INSERT INTO event_log (run_id, seq, type, data, created_at)
  VALUES (%(run_id)s, %(seq)s, %(type)s, %(data)s, to_timestamp(%(ts)s / 1000.0))
  ON CONFLICT (run_id, seq) DO NOTHING
  RETURNING 1
)
SELECT pg_notify(%(channel)s, %(payload)s) FROM inserted
"""
NOTIFY_ONLY = "SELECT pg_notify(%(channel)s, %(payload)s)"

_conn: psycopg.AsyncConnection | None = None
_conn_lock = asyncio.Lock()  # opening the shared connection
_db_lock = asyncio.Lock()    # one command at a time on the shared connection
_writers: set[asyncio.Task] = set()  # keep running writers referenced until they finish
_recorders: dict[str, "RunRecorder"] = {}
_loop: asyncio.AbstractEventLoop | None = None  # the app's event loop: all database work happens here


async def _connection() -> psycopg.AsyncConnection:
    """One shared autocommit connection for all reads and writes."""
    global _conn
    async with _conn_lock:
        if _conn is None or _conn.closed:
            _conn = await psycopg.AsyncConnection.connect(DATABASE_URL, autocommit=True)
    return _conn


async def _reset() -> None:
    """Drop a connection left in a bad state, so the next command opens a fresh one."""
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None


async def _fetch(sql: str, params: tuple) -> list[tuple]:
    """Run a read on the shared connection.

    Shielded: if the HTTP request that asked for it goes away (browser refresh),
    the query still finishes. Cancelling a query halfway would leave the shared
    connection stuck with "another command is already in progress".
    """

    async def run() -> list[tuple]:
        async with _db_lock:
            try:
                conn = await _connection()
                cur = await conn.execute(sql, params)
                return await cur.fetchall()
            except psycopg.Error:
                await _reset()
                raise

    return await asyncio.shield(asyncio.create_task(run()))


async def start() -> None:
    global _loop
    _loop = asyncio.get_running_loop()
    await _connection()  # open it at startup so the first write doesn't pay the connection cost


def record(run_id: str, e: Event) -> None:
    """Queue an event for a run. Callable from any thread or event loop.

    DBOS resumes a recovered workflow on its own background event loop, but our
    connection, locks and writer tasks belong to the app's loop, so the event is
    handed over with call_soon_threadsafe. Hand-offs keep their order.
    """
    _on_app_loop(lambda: _recorder(run_id).put(e))


def finish(run_id: str) -> None:
    """No more events for this run: flush its queue and stop its writer."""
    _on_app_loop(lambda: _recorders.pop(run_id).put(None) if run_id in _recorders else None)


def _on_app_loop(fn) -> None:
    try:
        on_app_loop = asyncio.get_running_loop() is _loop
    except RuntimeError:  # no loop in this thread
        on_app_loop = False
    if on_app_loop:
        fn()
    else:
        _loop.call_soon_threadsafe(fn)


def _recorder(run_id: str) -> "RunRecorder":
    if run_id not in _recorders:
        _recorders[run_id] = RunRecorder(run_id)
    return _recorders[run_id]


async def stop() -> None:
    global _conn
    if _writers:
        await asyncio.gather(*_writers, return_exceptions=True)
    if _conn:
        await _conn.close()
        _conn = None


async def read_events(run_id: str, after: int = 0) -> list[Event]:
    """Stored events of a run with seq > after, in order. Used for catch-up."""
    rows = await _fetch(
        "SELECT seq, type, data, extract(epoch FROM created_at) * 1000 FROM event_log "
        "WHERE run_id = %s AND seq > %s ORDER BY seq",
        (run_id, after),
    )
    return [Event(id=f"{run_id}-{seq}", seq=seq, type=type_, data=data, ts=float(ts)) for seq, type_, data, ts in rows]


class RunRecorder:
    """One run's write queue and the background task that drains it (lives on the app's loop)."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._queue: asyncio.Queue[Event | None] = asyncio.Queue()
        task = asyncio.create_task(self._write_all())
        _writers.add(task)
        task.add_done_callback(_writers.discard)

    def put(self, e: Event | None) -> None:
        self._queue.put_nowait(e)  # None = the writer stops after flushing everything before it

    async def _write_all(self) -> None:
        done = False
        while not done:
            batch = [await self._queue.get()]
            while not self._queue.empty():  # take everything that piled up during the last round trip
                batch.append(self._queue.get_nowait())
            if None in batch:
                done = True
                batch = batch[: batch.index(None)]
            if batch:
                await self._write_batch(_merge_deltas(batch))

    async def _write_batch(self, batch: list[Event]) -> None:
        async with _db_lock:
            for attempt in (1, 2):  # a second try on a fresh connection (e.g. Neon closed an idle one)
                try:
                    conn = await _connection()
                    async with conn.pipeline():
                        for e in batch:
                            await conn.execute(*self._statement(e))
                    return
                except Exception as exc:  # never break the run because the log is unavailable
                    log.warning("could not write %d events for run %s (attempt %d): %s",
                                len(batch), self.run_id, attempt, exc)
                    await _reset()

    def _statement(self, e: Event) -> tuple[str, dict[str, Any]]:
        payload = notify_payload(self.run_id, e.model_dump())
        if e.type in LIVE_ONLY:
            return NOTIFY_ONLY, {"channel": CHANNEL, "payload": payload}
        return INSERT_AND_NOTIFY, {
            "run_id": self.run_id,
            "seq": e.seq,
            "type": e.type,
            "data": json.dumps(e.data),
            "ts": e.ts,
            "channel": CHANNEL,
            "payload": payload,
        }


def _merge_deltas(batch: list[Event]) -> list[Event]:
    """Join consecutive message.delta events into one, so 20 words cost one notification."""
    merged: list[Event] = []
    for e in batch:
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and e.type == prev.type == "message.delta"
            and len(prev.data["text"]) < MAX_MERGED_DELTA
        ):
            prev.data = {"text": prev.data["text"] + e.data["text"]}
        else:
            merged.append(e.model_copy(deep=True))
    return merged
