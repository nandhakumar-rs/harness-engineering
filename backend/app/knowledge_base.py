"""A static key/value knowledge base, keyed by ticket category.

The searchKnowledgeBase tool looks up a category here and returns its articles.
A missing category yields an empty list (see tools.dispatch), so the model gets
a valid-but-empty result rather than an error.

Articles are deliberately short: whatever this returns is appended to the
conversation and re-sent on every following model call, so it costs tokens on
each iteration.
"""

KB: dict[str, list[dict[str, str]]] = {
    "billing": [
        {
            "title": "Duplicate charges",
            "body": "A second charge within minutes of the first is usually a pending "
                    "authorization, and it drops off in 3-5 business days without a refund. "
                    "If both charges have settled, we refund the duplicate immediately and "
                    "it posts to the original card in 5-10 business days.",
        },
        {
            "title": "Refund policy",
            "body": "Monthly plans: full refund within 14 days of the charge. Annual plans: "
                    "full refund within 30 days, prorated after that. Refunds always go back "
                    "to the original payment method; we cannot refund to a different card.",
        },
    ],
    "bug": [
        {
            "title": "Export button does nothing in Safari",
            "body": "Known issue on Safari 17 and later: 'Prevent cross-site tracking' blocks "
                    "the blob download the export uses. Workaround is Settings > Privacy, "
                    "untick 'Prevent cross-site tracking', then retry; or use Chrome or "
                    "Firefox. Fixed in release 2.4.1, shipping the week of 13 October.",
        },
        {
            "title": "Reporting a bug: what we need",
            "body": "Include browser and version, the exact steps, and any red errors in the "
                    "developer console. Response targets: 4 hours for data loss or an outage, "
                    "1 business day for a blocked workflow, 3 business days for everything else.",
        },
    ],
    "sales": [
        {
            "title": "Team and volume pricing",
            "body": "Pro is $24 per user per month. The Team tier starts at 10 seats and is "
                    "$19 per user per month. At 50 seats or more we discount 20% off Team, so "
                    "about $15.20 per user per month, and sales will confirm a written quote. "
                    "Paying annually gives two months free on any tier.",
        },
        {
            "title": "Trials and pilots",
            "body": "Every plan has a 14-day free trial with no card required. Teams evaluating "
                    "25 seats or more can request a 30-day pilot with onboarding support and an "
                    "invoice instead of a card.",
        },
    ],
    "account": [
        {
            "title": "Password reset email never arrives",
            "body": "Check spam first, then confirm the address is the one on the account. "
                    "Reset links expire after 60 minutes, so an old email will look broken. "
                    "Accounts on SSO cannot use password reset and must sign in through their "
                    "identity provider. Allowlisting no-reply@example.com fixes most corporate "
                    "mail filters.",
        },
        {
            "title": "Account locked after failed logins",
            "body": "Ten failed attempts lock an account for 30 minutes; the lock clears by "
                    "itself and support can clear it sooner on request. If two-factor codes are "
                    "rejected, the device clock is usually out of sync, so enable automatic time.",
        },
    ],
}
