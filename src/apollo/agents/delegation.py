"""Subagents exposed to the coordinator as tools: delegation with context quarantine."""

from __future__ import annotations

from typing import Any

from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage

from apollo.agents.subagents import build_crime_analyst, build_traffic_specialist
from apollo.middleware.errors import is_handled_tool_error


def _telemetry(agent_name: str, messages: list[Any]) -> dict[str, Any]:
    """Summarise what happened inside the specialist, for the UI and the report."""
    tool_calls = [
        call["name"] for m in messages if isinstance(m, AIMessage) for call in m.tool_calls
    ]
    citations: list[dict[str, Any]] = []
    events = [
        {"middleware": "ToolErrorMiddleware", "tool": m.name, "subagent": agent_name}
        for m in messages
        if is_handled_tool_error(m)
    ]
    for message in messages:
        if isinstance(message, ToolMessage) and isinstance(message.artifact, list):
            for citation in message.artifact:
                if citation not in citations:
                    citations.append(citation)
    return {
        "subagent": agent_name,
        "tool_calls": tool_calls,
        "quarantined_messages": len(messages) - 1,  # everything except the final answer
        "quarantined_chars": sum(len(str(m.content)) for m in messages[:-1]),
        "citations": citations,
        "middleware_events": events,
    }


def _delegate(agent: Any, task: str) -> tuple[str, dict[str, Any]]:
    if not task.strip():
        raise ValueError("The delegated task must not be empty.")
    # A fresh message list: the specialist sees only this task, not the conversation.
    result = agent.invoke({"messages": [{"role": "user", "content": task}]})
    messages = result["messages"]
    return messages[-1].text, _telemetry(agent.name, messages)


def build_delegation_tools(model: BaseChatModel | None = None) -> list:
    """Create the coordinator's delegation tools. `model` is injectable for tests."""
    traffic = build_traffic_specialist(model)
    crime = build_crime_analyst(model)

    @tool(response_format="content_and_artifact")
    def ask_traffic_specialist(task: str) -> tuple[str, dict[str, Any]]:
        """Delegate a question about traffic fines, demerit points or Road Traffic Act
        sections to the Traffic Fine Specialist, including combined-fine calculations.

        The specialist cannot see the conversation, so write a complete, self-contained
        task that repeats every offence, section number and figure the user mentioned.
        """
        return _delegate(traffic, task)

    @tool(response_format="content_and_artifact")
    def ask_crime_analyst(task: str) -> tuple[str, dict[str, Any]]:
        """Delegate a question about divisional crime statistics (2025 vs 2026) or
        Jamaica's historical national murder counts to the Crime Statistics Analyst.

        The specialist cannot see the conversation, so write a complete, self-contained
        task that names every division, crime category and year the user mentioned.
        """
        return _delegate(crime, task)

    return [ask_traffic_specialist, ask_crime_analyst]
