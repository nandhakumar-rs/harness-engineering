"""Runs live on their own, not inside an HTTP request.

    POST /api/runs             -> start_run(): starts the agent as a DBOS workflow
    GET  /api/runs/{id}/events -> watch_run(): catch up from event_log, then follow the bus

Closing the browser doesn't stop a run, any number of viewers can watch it,
and since Session 2 step 6 a server crash doesn't either: on restart, DBOS
resumes every unfinished workflow from its last finished step.
"""

import os
from typing import AsyncIterator

from dbos import DBOS, SetWorkflowID

from . import bus, event_store
from .agent import agent_workflow
from .events import Event

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "6"))
TERMINAL = {"run.completed", "run.failed"}


async def start_run(run_id: str, messages: list[dict]) -> bool:
    """Start a run as a workflow whose id is the run id.

    The id makes it idempotent: DBOS never runs the same workflow id twice, so a
    repeated start (double click, retried request) does nothing.
    """
    if await DBOS.get_workflow_status_async(run_id) is not None:
        return False
    with SetWorkflowID(run_id):
        await DBOS.start_workflow_async(agent_workflow, run_id, messages, MAX_ITERATIONS)
    return True


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
