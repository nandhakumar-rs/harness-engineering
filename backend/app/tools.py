"""The four support tools: JSON-schema definitions + Python handlers.

The model never runs this code. It only asks for a tool by name with
arguments; dispatch() is where the harness actually runs it.

Every tool returns a success response for now. No validation and no real
email service yet — those come in later sessions.
"""

import itertools
from typing import Any

from .knowledge_base import KB

CATEGORIES = list(KB.keys())  # ["billing", "bug", "sales", "account"]

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "classifyTicket",
            "description": "Classify a customer support ticket into exactly one category. "
            "Always call this first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The customer's message"},
                    "category": {
                        "type": "string",
                        "enum": CATEGORIES,
                        "description": "The category that best fits the message",
                    },
                },
                "required": ["message", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "searchKnowledgeBase",
            "description": "Look up help articles for a ticket category. Call this after "
            "classifyTicket, with the category it returned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CATEGORIES},
                    "query": {"type": "string", "description": "What the customer needs help with"},
                },
                "required": ["category", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draftReply",
            "description": "Save a draft email reply to the customer. Base it on the "
            "knowledge base articles you found. Returns a draftId.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The full email reply text"},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sendReply",
            "description": "Send a drafted reply to the customer. Call this after draftReply, "
            "with the draftId it returned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "draftId": {"type": "string", "description": "The id returned by draftReply"},
                },
                "required": ["draftId"],
            },
        },
    },
]


_draft_ids = itertools.count(1)
_sent_ids = itertools.count(1)


def classify_ticket(message: str, category: str) -> dict[str, Any]:
    return {"ok": True, "category": category}


def search_knowledge_base(category: str, query: str) -> dict[str, Any]:
    return {"ok": True, "articles": KB.get(category, [])}


def draft_reply(message: str) -> dict[str, Any]:
    return {"ok": True, "draftId": f"draft-{next(_draft_ids)}"}


def send_reply(draftId: str) -> dict[str, Any]:
    return {"ok": True, "sentId": f"sent-{next(_sent_ids)}"}


HANDLERS = {
    "classifyTicket": classify_ticket,
    "searchKnowledgeBase": search_knowledge_base,
    "draftReply": draft_reply,
    "sendReply": send_reply,
}


def dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    handler = HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    return handler(**args)
