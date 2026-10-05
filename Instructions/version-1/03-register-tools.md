# Step 3: Register the four tools

**File:** `backend/app/tools.py`

A tool has two halves:
1. a **definition** (JSON Schema) that tells the model the tool exists and what arguments it takes, and
2. a **handler** (a Python function) that actually runs when the model calls it.

The model never runs your code. It only *asks* for a tool by name, with arguments. Your harness decides what happens.

## The four tools

| name | arguments | returns (for now) |
|---|---|---|
| `classifyTicket` | `message: str` | `{"ok": True, "category": "billing"}` |
| `searchKnowledgeBase` | `category: str`, `query: str` | `{"ok": True, "articles": KB.get(category, [])}` |
| `draftReply` | `message: str` | `{"ok": True, "draftId": "draft-1"}` |
| `sendReply` | `draftId: str` | `{"ok": True, "sentId": "sent-1"}` |

**Every tool returns success.** There's no validation and no email service yet; those come in later sessions.

## 1. Definitions (Chat Completions format)

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "classifyTicket",
            "description": "Classify a customer support ticket into one category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The customer's message"},
                },
                "required": ["message"],
            },
        },
    },
    # searchKnowledgeBase: category should be an enum of your KB keys
    # draftReply
    # sendReply
]
```

Tips:
- **Descriptions are prompts.** "Call this after draftReply, with the draftId it returned" changes how the model behaves.
- Use `"enum": ["billing", "bug", "sales", "account"]` on `category` so the model can't make one up.

> `classifyTicket` returns a hard-coded category for now. Have it return what the *model* picked by adding a `category` argument with the enum, or keep it fixed and notice how the model behaves. Both are fine for Session 1.

## 2. Handlers + dispatch

```python
def classify_ticket(message: str) -> dict:
    return {"ok": True, "category": "billing"}

# ... search_knowledge_base, draft_reply, send_reply

HANDLERS = {
    "classifyTicket": classify_ticket,
    "searchKnowledgeBase": search_knowledge_base,
    "draftReply": draft_reply,
    "sendReply": send_reply,
}

def dispatch(name: str, args: dict) -> dict:
    handler = HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    return handler(**args)
```

`dispatch` is the single place where the harness turns "the model asked for X" into "X ran". Later sessions add validation, permissions and approvals **here**.

## Check
```bash
uv run python -c "
from app.tools import TOOLS, dispatch
print([t['function']['name'] for t in TOOLS])
print(dispatch('searchKnowledgeBase', {'category': 'billing', 'query': 'refund'}))"
```
