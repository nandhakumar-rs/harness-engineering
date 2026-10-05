"""The four tools: JSON-schema definitions plus the Python handlers behind them.

A tool has two halves that must agree:

  1. a DEFINITION in TOOLS — JSON Schema the model reads, deciding what to call
     and with which arguments. The model never runs any of this code.
  2. a HANDLER — the Python function the harness runs when the model asks.

dispatch() is the seam between them: the single place where "the model asked
for X" becomes "X ran". Later sessions add validation, permissions and
approvals here.

Every tool returns a success response for now. No validation and no real email
service yet — those come in later sessions.
"""

import uuid
from typing import Any

from .knowledge_base import KB

# The categories the model is allowed to choose. These MUST match the keys of
# KB, or a lookup silently returns no articles.
CATEGORIES = sorted(KB)


# --------------------------------------------------------------------------- #
# 1. Definitions — the model reads these.
#
# Descriptions are prompts. "Call this after draftReply, with the draftId it
# returned" genuinely changes which tool the model picks next, so the ordering
# of the workflow is encoded here as much as in the system prompt.
# --------------------------------------------------------------------------- #

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "classifyTicket",
            "description": (
                "Classify a customer support ticket into exactly one category. "
                "Call this first, before any other tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The customer's message, verbatim.",
                    },
                    "category": {
                        "type": "string",
                        "enum": CATEGORIES,
                        "description": "The single category that best fits the ticket.",
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
            "description": (
                "Look up help-centre articles for a ticket category. Call this after "
                "classifyTicket, using the category it returned."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": CATEGORIES,
                        "description": "The category returned by classifyTicket.",
                    },
                    "query": {
                        "type": "string",
                        "description": "What to look for, in a few words.",
                    },
                },
                "required": ["category", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draftReply",
            "description": (
                "Save a draft reply to the customer. Call this after searchKnowledgeBase, "
                "passing the full reply text you intend to send, grounded in the articles "
                "you found. Returns a draftId needed by sendReply."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The complete reply to send to the customer.",
                    },
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sendReply",
            "description": (
                "Send a reply that was already drafted. Call this last, passing the exact "
                "draftId that draftReply returned."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draftId": {
                        "type": "string",
                        "description": "The draftId returned by draftReply.",
                    },
                },
                "required": ["draftId"],
            },
        },
    },
]


# --------------------------------------------------------------------------- #
# 2. Handlers — the harness runs these.
#
# Parameter names must match the schema property names above, because dispatch
# calls handler(**args).
# --------------------------------------------------------------------------- #


def classify_ticket(message: str, category: str) -> dict[str, Any]:
    """Echo back the category the model chose."""
    return {"ok": True, "category": category}


def search_knowledge_base(category: str, query: str) -> dict[str, Any]:
    """Look up articles by category. `query` is accepted but not used for
    matching yet — the KB is keyed by category alone. Real search comes later."""
    return {"ok": True, "articles": KB.get(category, [])}


def draft_reply(message: str) -> dict[str, Any]:
    """Pretend to save a draft. The id is unique so you can verify the model
    carried it through to sendReply rather than guessing a constant."""
    return {"ok": True, "draftId": f"draft-{uuid.uuid4().hex[:6]}"}


def send_reply(draftId: str) -> dict[str, Any]:
    """Pretend to send. No email service and no validation of draftId yet."""
    return {"ok": True, "sentId": f"sent-{uuid.uuid4().hex[:6]}", "draftId": draftId}


HANDLERS = {
    "classifyTicket": classify_ticket,
    "searchKnowledgeBase": search_knowledge_base,
    "draftReply": draft_reply,
    "sendReply": send_reply,
}


def dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Turn a model's tool request into a real call. Raises on an unknown name."""
    handler = HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    return handler(**args)
