"""A static key/value knowledge base.

Keyed by ticket category. The searchKnowledgeBase tool looks up a category here
and returns its articles to the model, which quotes them in the reply.
"""

KB: dict[str, list[dict[str, str]]] = {
    "billing": [
        {
            "title": "Duplicate charges",
            "body": "A second charge is usually a pending authorization that drops off "
            "automatically within 3-5 days. If both charges have settled, we refund the "
            "duplicate right away; refunds post within 5-10 business days. Ask for the "
            "last four digits of the card and the charge dates to verify.",
        },
        {
            "title": "Refund policy",
            "body": "Full refund within 14 days of any charge, no questions asked. After 14 "
            "days we issue a prorated credit for the unused part of the billing period.",
        },
        {
            "title": "Updating payment method",
            "body": "Go to Settings > Billing > Payment method and click Replace card. The new "
            "card is used from the next invoice; failed invoices are retried within 24 hours.",
        },
    ],
    "bug": [
        {
            "title": "Export fails in Safari",
            "body": "Known issue: the Export button does nothing in Safari 17+. The team is "
            "tracking it. Workaround: use Chrome or Firefox, or use the CSV export option. "
            "We link the customer's report to the existing bug and follow up when it's fixed.",
        },
        {
            "title": "App is slow or not loading",
            "body": "Ask the customer to hard-refresh (Cmd/Ctrl+Shift+R) and clear the cache. "
            "Check status.example.com for an ongoing incident before escalating.",
        },
        {
            "title": "Reporting a bug",
            "body": "Collect: browser and version, OS, steps to reproduce, what they expected, "
            "what happened, and a screenshot or screen recording if possible.",
        },
    ],
    "sales": [
        {
            "title": "Team pricing",
            "body": "The Team plan is $20 per seat per month, billed monthly or annually (2 "
            "months free on annual). Volume discounts apply from 25 seats. We can send the "
            "pricing PDF and prepare a custom quote.",
        },
        {
            "title": "Enterprise plan",
            "body": "Enterprise adds SSO/SAML, a 99.9% uptime SLA, audit logs and a dedicated "
            "account manager. Pricing is custom; offer to book a call with sales.",
        },
    ],
    "account": [
        {
            "title": "Reset password",
            "body": "Use Forgot password on the login page. The reset link is valid for 1 hour. "
            "If the email doesn't arrive, check spam and allowlist no-reply@example.com, then "
            "request a new link.",
        },
        {
            "title": "Change email address",
            "body": "Go to Settings > Profile > Email. We send a confirmation link to the new "
            "address; the change applies once it's clicked.",
        },
        {
            "title": "Delete account",
            "body": "Account owners can delete the workspace from Settings > Danger zone. Data is "
            "kept for 30 days in case of a mistake, then permanently removed.",
        },
    ],
}
