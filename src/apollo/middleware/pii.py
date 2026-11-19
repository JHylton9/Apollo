"""PII protection: redact Jamaican TRNs and email addresses before any model sees them.

Two layers use the same patterns:

1. `redact_text` runs in ApolloSession *before* a message enters the agent graph. This
   matters because the checkpointer saves the incoming message before any middleware
   runs, so redaction inside the graph alone would leave raw PII in the saved history.
2. PIIMiddleware runs inside every agent (coordinator and specialists) as defence in
   depth, for any text that reaches an agent without passing through the session.
"""

from __future__ import annotations

import re

from langchain.agents.middleware import PIIMiddleware

# Order matters: emails first, because an email address can contain digit runs.
PII_PATTERNS: dict[str, str] = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    # Jamaican Taxpayer Registration Number: 9 digits, often written 123-456-789. The \b
    # boundaries stop it matching inside longer numbers such as 876-838-3589.
    "trn": r"\b\d{3}[- ]?\d{3}[- ]?\d{3}\b",
}

_COMPILED = {name: re.compile(pattern) for name, pattern in PII_PATTERNS.items()}


def placeholder(pii_type: str) -> str:
    # The same placeholder format PIIMiddleware's "redact" strategy produces.
    return f"[REDACTED_{pii_type.upper()}]"


def redact_text(text: str) -> tuple[str, list[str]]:
    """Return the text with PII replaced, and the PII types that were found."""
    found: list[str] = []
    for name, pattern in _COMPILED.items():
        text, count = pattern.subn(placeholder(name), text)
        if count:
            found.append(name)
    return text, found


def build_pii_middleware() -> list[PIIMiddleware]:
    """One PIIMiddleware per PII type, redacting user input before each model call."""
    return [
        PIIMiddleware(name, detector=pattern, strategy="redact", apply_to_input=True)
        for name, pattern in PII_PATTERNS.items()
    ]
