"""Session 1 — TODO: register the four tools.

1. TOOLS: JSON-schema tool definitions in the Chat Completions format:
   {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}

   - classifyTicket(message)              -> {"ok": True, "category": "billing" | "bug" | "sales" | "account"}
   - searchKnowledgeBase(category, query) -> {"ok": True, "articles": [...]}   (reads knowledge_base.KB)
   - draftReply(message)                  -> {"ok": True, "draftId": "..."}
   - sendReply(draftId)                   -> {"ok": True, "sentId": "..."}

   For now every tool just returns a success response. No validation and no
   real email service yet — those come in later sessions.

2. dispatch(name, args): look up the Python handler by name and call it.
"""

from typing import Any

TOOLS: list[dict[str, Any]] = []


def dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    raise NotImplementedError("Session 1: implement the tool handlers and dispatch")
