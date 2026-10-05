"""A scripted fake run so the UI works before any LLM is wired up.

It emits exactly the events a real agent run will emit. In session 1 you
replace this with app/agent.py: same events, real model.
"""

import asyncio
import json
import uuid
from typing import AsyncIterator

from .events import Event, event

FAKE_STEPS = [
    ("classifyTicket", {"message": "I was charged twice this month"}, {"ok": True, "category": "billing"}),
    ("searchKnowledgeBase", {"category": "billing", "query": "duplicate charge"}, {"ok": True, "articles": ["Duplicate charges"]}),
    ("draftReply", {"message": "Hi, thanks for reaching out..."}, {"ok": True, "draftId": "draft-1"}),
    ("sendReply", {"draftId": "draft-1"}, {"ok": True, "sentId": "sent-1"}),
]

FAKE_ANSWER = (
    "This is a scripted fake run from app/fake_agent.py. "
    "No model was called. In session 1 you'll replace it with a real agent loop "
    "that classifies the ticket, searches the knowledge base, drafts a reply and sends it."
)


async def run_fake_agent(messages: list[dict], max_iterations: int = 6) -> AsyncIterator[Event]:
    run_id = uuid.uuid4().hex[:8]
    yield event("run.started", runId=run_id)

    iteration = 0
    for name, args, result in FAKE_STEPS:
        iteration += 1
        yield event("iteration.started", iteration=iteration, max=max_iterations)
        yield event("thinking", status="started")
        await asyncio.sleep(0.6)
        yield event("thinking", status="stopped")

        call_id = f"call_{uuid.uuid4().hex[:16]}"
        yield event("tool.requested", toolCallId=call_id, name=name, args=args)
        await asyncio.sleep(0.4)
        yield event("tool.completed", toolCallId=call_id, result=result)

    iteration += 1
    yield event("iteration.started", iteration=iteration, max=max_iterations)
    yield event("thinking", status="started")
    await asyncio.sleep(0.5)
    yield event("thinking", status="stopped")
    for word in FAKE_ANSWER.split(" "):
        yield event("message.delta", text=word + " ")
        await asyncio.sleep(0.03)
    yield event("message.completed", text=FAKE_ANSWER)

    yield event("run.completed", runId=run_id, iterations=iteration)
