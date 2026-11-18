"""High-risk action tools: they create official records, so every call is human-reviewed."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from langchain.tools import tool

from apollo.retrieval.tables import normalize_section
from apollo.tools import _runtime

_EMAIL = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


def _record(kind: str, prefix: str, payload: dict[str, Any]) -> str:
    """Append an action to data/actions/<kind>.jsonl and return its reference number."""
    now = datetime.now(UTC)
    reference = f"{prefix}-{now:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    entry = {"reference": reference, "created_at": now.isoformat(), **payload}
    folder = _runtime.get_settings().actions_dir
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f"{kind}.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return reference


def _known_division(location: str) -> str:
    key = " ".join(re.findall(r"[a-z0-9]+", location.casefold()))
    for division in _runtime.get_records().divisions:
        if division.division != "Grand Total" and (
            " ".join(re.findall(r"[a-z0-9]+", division.division.casefold())) == key
        ):
            return division.division
    raise ValueError(f"'{location}' is not a JCF police division; give a division name.")


@tool
def issue_fine_notice(
    section: str,
    offence: str,
    location: str,
    driver_name: str | None = None,
    vehicle_plate: str | None = None,
) -> str:
    """Issue an official JCF traffic violation notice. HIGH RISK: requires human approval.

    The fine and demerit points are taken from the official schedule, never from the
    caller, so a notice cannot be issued for a wrong amount.
    """
    key = normalize_section(section)
    matches = [r for r in _runtime.get_records().fines if normalize_section(r.section) == key]
    if not matches:
        raise ValueError(f"Section {section} is not in the fine schedule; notice not issued.")
    words = set(re.findall(r"[a-z0-9]+", offence.casefold()))
    best = max(
        matches, key=lambda r: len(words & set(re.findall(r"[a-z0-9]+", r.offence.casefold())))
    )
    reference = _record(
        "fine_notices",
        "FN",
        {
            "section": best.section,
            "offence": best.offence,
            "fine": best.fine,
            "points": best.points,
            "location": location,
            "driver_name": driver_name,
            "vehicle_plate": vehicle_plate,
        },
    )
    return (
        f"Notice {reference} issued: {best.offence} ({best.section}), fine ${best.fine:,}, "
        f"{best.points} demerit points, at {location}."
    )


@tool
def notify_email(to: str, subject: str, body: str) -> str:
    """Send an official email notification, e.g. to the traffic department. HIGH RISK:
    requires human approval. Simulated: the message is written to the outbox log.
    """
    if not _EMAIL.match(to.strip()):
        raise ValueError(f"'{to}' is not a valid email address.")
    if not subject.strip() or not body.strip():
        raise ValueError("Email subject and body must not be empty.")
    reference = _record("outbox", "EM", {"to": to.strip(), "subject": subject, "body": body})
    return f"Email {reference} queued to {to.strip()} with subject '{subject}'."


@tool
def log_sighting_report(
    suspect_name: str, location: str, details: str = "", anonymous: bool = True
) -> str:
    """Log a citizen sighting report for a wanted person. HIGH RISK: requires human approval.

    `location` must be a JCF police division, e.g. "Kingston Central" or "St. Andrew South".
    """
    if not suspect_name.strip():
        raise ValueError("A suspect name is required.")
    division = _known_division(location)
    reference = _record(
        "sighting_reports",
        "SR",
        {
            "suspect_name": suspect_name.strip(),
            "division": division,
            "details": details,
            "anonymous": anonymous,
        },
    )
    return f"Sighting report {reference} logged for {suspect_name.strip()} in {division}."


ACTION_TOOLS = [issue_fine_notice, notify_email, log_sighting_report]

# Module 3 configures HumanInTheLoopMiddleware(interrupt_on=...) from this set.
HIGH_RISK_TOOL_NAMES = frozenset(t.name for t in ACTION_TOOLS)