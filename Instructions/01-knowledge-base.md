# Step 1: Build the knowledge base

**File:** `backend/app/knowledge_base.py`

The agent needs something to look answers up in. For now it's a plain Python dict. A vector store or database comes much later.

## What to do

1. Pick four ticket categories: `billing`, `bug`, `sales`, `account`.
2. Under each one, write **2–3 short articles**, each with a `title` and a `body`.
3. Write the bodies the way a support lead would: concrete numbers, steps and policies. The model will quote them in its replies.

```python
KB: dict[str, list[dict[str, str]]] = {
    "billing": [
        {
            "title": "Duplicate charges",
            "body": "A second charge is usually a pending authorization that drops off "
                    "within 3-5 days. If both charges settled, we refund the duplicate "
                    "immediately; refunds post in 5-10 business days.",
        },
        {"title": "Refund policy", "body": "..."},
    ],
    "bug": [
        {"title": "Export fails in Safari", "body": "..."},
    ],
    "sales": [
        {"title": "Team pricing", "body": "..."},
    ],
    "account": [
        {"title": "Reset password", "body": "..."},
    ],
}
```

## Things to think about
- What should happen when the model asks for a category that **doesn't exist**? For now, return an empty list. Validation comes in a later session.
- Keep articles short. Whatever the tool returns gets sent back to the model, and that costs tokens.

## Check
```bash
cd backend
uv run python -c "from app.knowledge_base import KB; print({k: len(v) for k, v in KB.items()})"
# {'billing': 2, 'bug': 2, 'sales': 2, 'account': 2}
```
