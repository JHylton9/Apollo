"""Phase 2 evaluation: run every spec test case end to end and record the evidence."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from langchain_core.runnables import RunnableConfig

from apollo.agents.session import ApolloSession, PendingAction, Turn, approve, edit

MAX_REVIEW_ROUNDS = 5


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


@dataclass
class CaseResult:
    id: str
    category: str
    question: str
    passed: bool = False
    checks: list[Check] = field(default_factory=list)
    answer: str | None = None
    subagents: list[str] = field(default_factory=list)
    delegations: list[dict[str, Any]] = field(default_factory=list)
    middleware: list[str] = field(default_factory=list)
    reviews: list[dict[str, str]] = field(default_factory=list)
    seconds: float = 0.0
    error: str | None = None


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def _decide(review: dict[str, Any], pending: list[PendingAction]) -> list[dict[str, Any]]:
    decisions = []
    for action in pending:
        if review.get("policy") == "edit" and action.name == review.get("tool"):
            decisions.append(edit(action.name, {**action.args, **review["args"]}))
        else:
            decisions.append(approve())
    return decisions


def _clean(text: str | None) -> str:
    # Ignore Markdown emphasis and letter case when looking for expected values.
    return (text or "").replace("*", "").casefold()


def _records(actions_dir: Path, kind: str) -> list[dict[str, Any]]:
    path = actions_dir / f"{kind}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _checks(
    expect: dict[str, Any], result: CaseResult, session: ApolloSession, actions_dir: Path
) -> list[Check]:
    checks: list[Check] = []
    answer = _clean(result.answer)
    if subagent := expect.get("subagent"):
        checks.append(
            Check(
                f"delegated to {subagent}",
                subagent in result.subagents,
                f"delegated to: {', '.join(result.subagents) or 'none'}",
            )
        )
    for value in expect.get("answer_contains", []):
        checks.append(Check(f"answer contains '{value}'", _clean(value) in answer, ""))
    for value in expect.get("answer_excludes", []):
        checks.append(Check(f"answer omits '{value}'", _clean(value) not in answer, ""))
    for name in expect.get("middleware", []):
        checks.append(
            Check(
                f"{name} fired",
                name in result.middleware,
                f"fired: {', '.join(result.middleware) or 'none'}",
            )
        )
    reviewed = {review["tool"] for review in result.reviews}
    for tool in expect.get("paused_for", []):
        checks.append(
            Check(
                f"paused for review of {tool}",
                tool in reviewed,
                f"reviewed: {', '.join(sorted(reviewed)) or 'none'}",
            )
        )
    for kind, fields in expect.get("records", {}).items():
        found = any(
            all(record.get(key) == value for key, value in fields.items())
            for record in _records(actions_dir, kind)
        )
        checks.append(Check(f"{kind} record with {fields}", found, ""))
    if raw_values := expect.get("never_stored"):
        history = " ".join(
            str(message.content)
            for snapshot in session.agent.get_state_history(cast(RunnableConfig, session.config))
            for message in snapshot.values.get("messages", [])
        )
        for value in raw_values:
            checks.append(
                Check(f"'{value}' never stored in any checkpoint", value not in history, "")
            )
    return checks


def _record_turn(result: CaseResult, turn: Turn) -> None:
    for delegation in turn.delegations:
        result.delegations.append(
            {
                key: delegation.get(key)
                for key in (
                    "subagent",
                    "tool_calls",
                    "quarantined_messages",
                    "quarantined_chars",
                    "answer_chars",
                )
            }
        )
        if delegation["subagent"] not in result.subagents:
            result.subagents.append(delegation["subagent"])
    for event in turn.middleware_events:
        if event["middleware"] not in result.middleware:
            result.middleware.append(event["middleware"])


def run_case(
    case: dict[str, Any], session_factory: Callable[[], ApolloSession], actions_dir: Path
) -> CaseResult:
    result = CaseResult(case["id"], case["category"], case["question"])
    started = time.perf_counter()
    try:
        session = session_factory()
        turn = session.ask(case["question"])
        _record_turn(result, turn)
        rounds = 0
        while turn.awaiting_review and rounds < MAX_REVIEW_ROUNDS:
            decisions = _decide(case.get("review", {"policy": "approve"}), turn.pending)
            result.reviews += [
                {"tool": a.name, "decision": d["type"]}
                for a, d in zip(turn.pending, decisions, strict=True)
            ]
            turn = session.review(decisions)
            _record_turn(result, turn)
            rounds += 1
        result.answer = turn.answer
        result.checks = _checks(case.get("expect", {}), result, session, actions_dir)
        result.passed = all(check.passed for check in result.checks)
    except Exception as error:  # a crash is a recorded failure, not the end of the run
        result.error = f"{type(error).__name__}: {error}"
    result.seconds = round(time.perf_counter() - started, 1)
    return result


def evaluate(
    cases: list[dict[str, Any]],
    session_factory: Callable[[], ApolloSession],
    actions_dir: Path,
    on_result: Callable[[CaseResult], None] | None = None,
) -> dict[str, Any]:
    results = []
    for case in cases:
        result = run_case(case, session_factory, actions_dir)
        results.append(result)
        if on_result:
            on_result(result)
    delegations = [d for r in results for d in r.delegations]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": sum(r.passed for r in results),
        "total": len(results),
        "quarantine": {
            "delegations": len(delegations),
            "coordinator_received_chars": sum(d["answer_chars"] or 0 for d in delegations),
            "quarantined_chars": sum(d["quarantined_chars"] or 0 for d in delegations),
        },
        "results": [asdict(r) for r in results],
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 2 evaluation",
        "",
        f"Generated {report['generated_at']}. **{report['passed']}/{report['total']} cases "
        "passed.** Each case ran in a fresh conversation against the live model.",
        "",
        "| Case | Category | Result | Subagents | Middleware fired | Officer decisions | Time |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in report["results"]:
        outcome = "PASS" if r["passed"] else ("ERROR" if r["error"] else "FAIL")
        reviews = ", ".join(f"{v['tool']}: {v['decision']}" for v in r["reviews"]) or "-"
        lines.append(
            f"| {r['id']} | {r['category']} | {outcome} | {', '.join(r['subagents']) or '-'} "
            f"| {', '.join(r['middleware']) or '-'} | {reviews} | {r['seconds']}s |"
        )
    q = report["quarantine"]
    received, kept = q["coordinator_received_chars"], q["quarantined_chars"]
    share = f"{kept / (kept + received):.0%}" if kept + received else "n/a"
    lines += [
        "",
        "## Context quarantine",
        "",
        f"Across {q['delegations']} delegations, the coordinator received **{received:,}** "
        f"characters of specialist answers, while **{kept:,}** characters of intermediate "
        f"tool calls and results stayed inside the specialists ({share} of the total). "
        "Prompts and tool schemas of the specialists are not counted.",
        "",
        "| Case | Subagent | Tool calls | Coordinator received | Kept in specialist |",
        "|---|---|---|---|---|",
    ]
    for r in report["results"]:
        for d in r["delegations"]:
            lines.append(
                f"| {r['id']} | {d['subagent']} | {len(d['tool_calls'] or [])} "
                f"| {d['answer_chars']:,} chars | {d['quarantined_messages']} messages, "
                f"{d['quarantined_chars']:,} chars |"
            )
    lines += ["", "## Cases", ""]
    for r in report["results"]:
        lines += [f"### {r['id']}", "", f"**Question:** {r['question']}", ""]
        if r["error"]:
            lines += [f"**Error:** `{r['error']}`", ""]
        for check in r["checks"]:
            mark = "✅" if check["passed"] else "❌"
            detail = f" ({check['detail']})" if check["detail"] else ""
            lines.append(f"- {mark} {check['name']}{detail}")
        lines += ["", "**Answer:**", "", "> " + (r["answer"] or "(none)").replace("\n", "\n> "), ""]
    return "\n".join(lines) + "\n"
