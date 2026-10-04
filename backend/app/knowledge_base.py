"""Session 1 — TODO: a static key/value knowledge base.

Key it by ticket category (e.g. "billing", "bug", "sales", "account") and put a
few short articles under each one. The searchKnowledgeBase tool will look up a
category here and return the matching articles.

Example shape:

KB = {
    "billing": [
        {"title": "Duplicate charges", "body": "A duplicate charge is usually ..."},
    ],
}
"""

KB: dict[str, list[dict[str, str]]] = {}
