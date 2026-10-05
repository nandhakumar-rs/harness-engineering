"""Runs live on their own, not inside an HTTP request.

    POST /api/runs            -> start_run(): starts the agent as a background task
    GET  /api/runs/{id}/events -> watch_run(): catch up from event_log, then follow the bus

Closing the browser no longer stops a run, and any number of viewers can
watch it, joining at any point. (A server crash still kills it: that's what
the workflow step fixes.)
"""

import asyncio
import logging
import os
from typing import AsyncIterator

from . import bus, event_store
from .events import Event, event

log = logging.getLogger("harness.runs")

# Set to True to go back to the scripted fake run in app/fake_agent.py.
USE_FAKE_AGENT = False

if USE_FAKE_AGENT:
    from .fake_agent import run_fake_agent as agent
else:
    from .agent import run_agent as agent

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "6"))
TERMINAL = {"run.completed", "run.failed"}

_active: dict[str, asyncio.Task] = {}


async def start_run(run_id: str, messages: list[dict]) -> bool:
    """Start a run in the background. Starting the same run_id twice does nothing."""
    if run_id in _active or await event_store.run_exists(run_id):
        return False
    _active[run_id] = asyncio.create_task(_execute(run_id, messages))
    _active[run_id].add_done_callback(lambda _: _active.pop(run_id, None))
    return True


async def _execute(run_id: str, messages: list[dict]) -> None:
    recorder = event_store.RunRecorder(run_id)
    try:
        async for e in agent(run_id, messages, max_iterations=MAX_ITERATIONS):
            recorder.record(e)
    except Exception as exc:
        log.exception("run %s crashed", run_id)
        recorder.record(event("run.failed", runId=run_id, error=f"{type(exc).__name__}: {exc}"))
    finally:
        recorder.finish()


async def watch_run(run_id: str, after: int = 0) -> AsyncIterator[Event]:
    """Every event of a run with seq > after, then live events until the run ends.

    Subscribe FIRST, then read the log: anything committed after the read is
    already waiting in the queue, so nothing falls in the gap. Events seen in
    both places are skipped by seq.
    """
    async with bus.subscribe(run_id) as queue:
        last = after
        for e in await event_store.read_events(run_id, after):
            last = e.seq
            yield e
            if e.type in TERMINAL:
                return

        while True:
            e = await queue.get()
            if "ref" in e:  # too big for a notification: load the row itself
                rows = await event_store.read_events(run_id, e["ref"]["seq"] - 1)
                e = rows[0].model_dump() if rows else None
                if e is None:
                    continue
            e = Event(**e)
            if e.seq is not None:
                if e.seq <= last:
                    continue  # already sent during catch-up
                last = e.seq
            yield e
            if e.type in TERMINAL:
                return
