"""A conversation with the coordinator, including human review of paused actions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command

from apollo.agents.coordinator import build_coordinator, thread_config
from apollo.llm import get_chat_model
from apollo.middleware import coordinator_middleware, redact_text
from apollo.middleware.errors import is_handled_tool_error
from apollo.middleware.limits import limit_hit

Decision = dict[str, Any]


def approve() -> Decision:
    return {"type": "approve"}


def edit(name: str, args: dict[str, Any]) -> Decision:
    return {"type": "edit", "edited_action": {"name": name, "args": args}}


def reject(message: str) -> Decision:
    return {"type": "reject", "message": message}


def respond(message: str) -> Decision:
    return {"type": "respond", "message": message}


@dataclass(frozen=True)
class PendingAction:
    """One tool call waiting for a reviewer's decision."""

    name: str
    args: dict[str, Any]
    description: str
    allowed_decisions: list[str]


@dataclass
class Turn:
    """What happened in one step of the conversation, for display and telemetry."""

    answer: str | None
    pending: list[PendingAction] = field(default_factory=list)
    tool_calls: list[str] = field(default_factory=list)
    delegations: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    middleware_events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def awaiting_review(self) -> bool:
        return bool(self.pending)


def _pending_actions(result: dict[str, Any]) -> list[PendingAction]:
    actions: list[PendingAction] = []
    for interrupt in result.get("__interrupt__", ()):
        request = interrupt.value
        for action, config in zip(
            request["action_requests"], request["review_configs"], strict=True
        ):
            actions.append(
                PendingAction(
                    name=action["name"],
                    args=dict(action["args"]),
                    description=action.get("description", ""),
                    allowed_decisions=list(config["allowed_decisions"]),
                )
            )
    return actions


def _limit_events(message: AIMessage) -> list[dict[str, Any]]:
    """An event if this message is the one a call limit ends a run with."""
    name = limit_hit(message.text)
    return [{"middleware": name, "detail": message.text}] if name else []


def _summarise(new_messages: list[Any], result: dict[str, Any]) -> Turn:
    tool_calls: list[str] = []
    delegations: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for message in new_messages:
        if message.additional_kwargs.get("lc_source") == "summarization":
            events.append({"middleware": "SummarizationMiddleware"})
        if isinstance(message, AIMessage):
            tool_calls += [call["name"] for call in message.tool_calls]
            events += _limit_events(message)
        elif isinstance(message, ToolMessage):
            if is_handled_tool_error(message):
                events.append({"middleware": "ToolErrorMiddleware", "tool": message.name})
            artifact = message.artifact
            found = []
            if isinstance(artifact, dict) and "subagent" in artifact:
                delegations.append(artifact)
                events += artifact.get("middleware_events", [])
                found = artifact.get("citations", [])
            elif isinstance(artifact, list):
                found = artifact
            citations += [c for c in found if c not in citations]
    pending = _pending_actions(result)
    last = new_messages[-1] if new_messages else None
    # While paused, the last message is the model's tool request, not an answer.
    answer = None if pending or not isinstance(last, AIMessage) else last.text
    return Turn(answer, pending, tool_calls, delegations, citations, events)


class ApolloSession:
    def __init__(self, agent: Any | None = None, thread_id: str | None = None) -> None:
        self.agent = agent or build_coordinator(
            middleware=coordinator_middleware(summary_model=get_chat_model())
        )
        self.thread_id = thread_id or uuid.uuid4().hex
        self.config = thread_config(self.thread_id)
        self.pending: list[PendingAction] = []

    def _message_ids(self) -> set[str]:
        return {m.id for m in self.agent.get_state(self.config).values.get("messages", [])}

    def _run(self, payload: Any) -> Turn:
        # Identify this step's messages by ID, not by position: summarization replaces
        # older messages, so the history can get shorter between turns.
        before = self._message_ids()
        result = self.agent.invoke(payload, self.config)
        new_messages = [m for m in result["messages"] if m.id not in before]
        turn = _summarise(new_messages, result)
        self.pending = turn.pending
        return turn

    def ask(self, text: str) -> Turn:
        if self.pending:
            raise RuntimeError("Review the pending action(s) before sending a new message.")
        if not text.strip():
            raise ValueError("The message must not be empty.")
        # Redact before the message enters the graph: the checkpointer saves incoming
        # messages before any middleware runs, so this keeps raw PII out of the history.
        text, redacted = redact_text(text)
        turn = self._run({"messages": [{"role": "user", "content": text}]})
        if redacted:
            turn.middleware_events.insert(0, {"middleware": "PII", "redacted": redacted})
        return turn

    def review(self, decisions: list[Decision]) -> Turn:
        if not self.pending:
            raise RuntimeError("There is nothing waiting for review.")
        if len(decisions) != len(self.pending):
            raise ValueError(
                f"Expected {len(self.pending)} decision(s), one per pending action, "
                f"in order; got {len(decisions)}."
            )
        for decision, action in zip(decisions, self.pending, strict=True):
            if decision["type"] not in action.allowed_decisions:
                raise ValueError(f"'{decision['type']}' is not allowed for {action.name}.")
        # Record each officer decision, so the UI can show when the HITL gate acted.
        reviewed = [
            {"middleware": "HumanInTheLoopMiddleware", "tool": a.name, "decision": d["type"]}
            for a, d in zip(self.pending, decisions, strict=True)
        ]
        turn = self._run(Command(resume={"decisions": decisions}))
        turn.middleware_events[:0] = reviewed
        return turn
