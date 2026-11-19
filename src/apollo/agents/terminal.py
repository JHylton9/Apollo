"""Terminal chat with officer review of paused actions (`uv run apollo chat`).

A stand-in for the Phase 3 dashboard: same ApolloSession, rendered with Rich.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from apollo.agents.session import (
    ApolloSession,
    PendingAction,
    Turn,
    approve,
    edit,
    reject,
    respond,
)

CHOICES = {"a": "approve", "e": "edit", "r": "reject", "p": "respond"}


def _coerce(original: Any, text: str) -> Any:
    """Convert an edited value back to the argument's original type."""
    if isinstance(original, bool):
        return text.strip().casefold() in {"true", "yes", "y", "1"}
    if isinstance(original, int):
        return int(text)
    if original is None and not text.strip():
        return None
    return text


def _show_action(console: Console, index: int, total: int, action: PendingAction) -> None:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Argument")
    table.add_column("Proposed value", overflow="fold")
    for name, value in action.args.items():
        table.add_row(name, str(value))
    title = f"Review {index}/{total}: {action.name}"
    console.print(Panel(table, title=title, subtitle=action.description.splitlines()[0]))


def _prompt_value(console: Console, name: str, value: Any) -> str:
    """Ask for one edited argument, catching the easy slip of typing its name."""
    while (text := typer.prompt(f"  {name}", default=str(value))).strip() == name:
        console.print(f"  That is the argument's name. Press Enter to keep {escape(f'[{value}]')}.")
    return text


def _decide(console: Console, action: PendingAction) -> dict[str, Any]:
    keys = [key for key, name in CHOICES.items() if name in action.allowed_decisions]
    labels = ", ".join(f"[{key}] {CHOICES[key]}" for key in keys)
    while (choice := typer.prompt(f"Decision ({labels})").strip().casefold()) not in keys:
        console.print(f"Please type one of: {', '.join(keys)}")
    if choice == "a":
        return approve()
    if choice == "e":
        console.print(
            "For each argument, press Enter to keep the value shown in [brackets], "
            "or type the new value (not the argument name).",
            markup=False,
        )
        args = {
            name: _coerce(value, _prompt_value(console, name, value))
            for name, value in action.args.items()
        }
        return edit(action.name, args)
    if choice == "r":
        return reject(typer.prompt("Reason for rejecting"))
    return respond(typer.prompt("Your response (returned to the agent as the tool result)"))


def _show_turn(console: Console, turn: Turn) -> None:
    for delegation in turn.delegations:
        console.print(
            f"[cyan]● delegated to {delegation['subagent']}[/] "
            f"(tools: {', '.join(delegation['tool_calls']) or 'none'}; "
            f"{delegation['quarantined_messages']} messages kept out of the coordinator)"
        )
    for event in turn.middleware_events:
        if event["middleware"] == "PII":
            kinds = ", ".join(kind.upper() for kind in event["redacted"])
            console.print(f"[magenta]◆ PII[/] redacted before the model or history saw it: {kinds}")
            continue
        if event["middleware"] == "SummarizationMiddleware":
            console.print(
                "[magenta]◆ Summarization[/] older messages were condensed into a summary"
            )
            continue
        if event["middleware"] in {"ToolCallLimitMiddleware", "ModelCallLimitMiddleware"}:
            where = f" in {event['subagent']}" if event.get("subagent") else ""
            console.print(
                f"[magenta]◆ {event['middleware']}[/] stopped the run{where}: {event['detail']}"
            )
            continue
        if event["middleware"] == "HumanInTheLoopMiddleware":
            console.print(
                f"[magenta]◆ HITL[/] officer decision on {event['tool']}: {event['decision']}"
            )
            continue
        where = f" inside {event['subagent']}" if event.get("subagent") else ""
        console.print(
            f"[magenta]◆ {event['middleware']}[/] handled an error from "
            f"{event['tool']}{where}; the model received feedback instead of a crash"
        )
    if turn.answer:
        # Text() shows the answer literally, so brackets in it are not read as Rich markup.
        console.print(Panel(Text(turn.answer), title="Apollo", border_style="green"))
    if turn.citations:
        sources = sorted(
            {f"{c['source']}" + (f" p{c['page']}" if c.get("page") else "") for c in turn.citations}
        )
        console.print(f"[dim]Retrieved sources: {'; '.join(sources)}[/]")


def run_chat(console: Console, session_factory: Callable[[], ApolloSession] | None = None) -> None:
    # Looked up at call time so tests can substitute a session with a scripted model.
    session = (session_factory or ApolloSession)()
    console.print(f"[bold]Apollo[/] thread {session.thread_id[:8]}. Type 'exit' to quit.")
    while True:
        text = typer.prompt("You", default="", show_default=False).strip()
        if text.casefold() in {"exit", "quit"}:
            break
        if not text:
            continue
        turn = session.ask(text)
        while turn.awaiting_review:
            _show_turn(console, turn)
            console.print("[yellow]⏸ Paused: officer review required before this runs.[/]")
            decisions = []
            for index, action in enumerate(turn.pending, start=1):
                _show_action(console, index, len(turn.pending), action)
                decisions.append(_decide(console, action))
            turn = session.review(decisions)
        _show_turn(console, turn)
