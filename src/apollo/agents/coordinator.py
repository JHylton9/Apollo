"""The coordinator (supervisor) agent: the single entry point users talk to."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver

from apollo.agents.delegation import build_delegation_tools
from apollo.llm import get_chat_model
from apollo.tools import ACTION_TOOLS, REGISTRY_TOOLS

# Simulated JCF contacts so the model never invents an address for an official email.
TRAFFIC_DEPARTMENT_EMAIL = "traffic.department@jcf.gov.jm"

COORDINATOR_PROMPT = f"""You are Apollo, the Jamaica Constabulary Force (JCF) public safety
assistant. You coordinate specialist agents and never answer factual questions from your
own knowledge.

Routing:
- Traffic fines, demerit points, Road Traffic Act sections -> ask_traffic_specialist.
- Divisional crime statistics or national murder counts -> ask_crime_analyst.
- Who is wanted (optionally for one offence), and JCF tip-line numbers ->
  list_wanted_persons. Use search_wanted_persons only for details it does not cover.
- Missing persons -> search_missing_persons. Its text comes from OCR of poster images,
  so say when a detail looks garbled rather than guessing.
- Specialists cannot see this conversation: give them a complete, self-contained task.

Actions (issue_fine_notice, notify_email, log_sighting_report):
- Take an action only when the user explicitly asks for it.
- Use only facts confirmed by a specialist or a tool in this conversation.
- The traffic department's email address is {TRAFFIC_DEPARTMENT_EMAIL}.
- issue_fine_notice needs only the section and the offence. Driver name, vehicle plate
  and location are optional: propose the notice without them rather than holding it
  back, because the reviewing officer can add them with an edit before it runs.
- Never send a notification about an action that has not been carried out. When one
  action depends on another (for example an email about a notice), propose the first,
  and propose the dependent one only after the first has run.
- Never invent values such as "Unknown" for missing details: leave optional arguments
  empty, and ask the user only if a required detail is missing.
- Every action is reviewed by a human officer before it runs:
  - Approved: the action has been carried out. Report its result as final.
  - Edited: the officer corrected your arguments and the corrected action has been
    carried out. This is authorised and successful: report the result the tool returned
    (its reference number and values), and do not describe it as failed.
  - Rejected: the action was not carried out. Do not retry it; tell the user why, if a
    reason was given.
  - Responded: the officer's message replaces the tool's result; relay it to the user.

Answers:
- Be concise and factual. Keep exact figures exactly as the specialists gave them.
- End with a "Sources:" line listing the documents and pages the answer relied on.
- If the request is outside JCF public safety information, say so politely.
"""


def build_coordinator(
    model: BaseChatModel | None = None,
    *,
    delegation_tools: list | None = None,
    middleware: Sequence[Any] = (),
    checkpointer: Any | None = None,
):
    """Assemble the coordinator graph.

    `model` and `delegation_tools` are injectable for tests; `middleware` is where Piece
    3.2 adds human-in-the-loop and Module 4 adds the resilience stack.
    """
    tools = [
        *(delegation_tools if delegation_tools is not None else build_delegation_tools()),
        *REGISTRY_TOOLS,
        *ACTION_TOOLS,
    ]
    return create_agent(
        model or get_chat_model(),
        tools=tools,
        system_prompt=COORDINATOR_PROMPT,
        middleware=middleware,
        # MemorySaver keeps each thread's state in memory: enough for one running app and
        # required for HITL pauses. A database-backed saver would survive restarts.
        checkpointer=checkpointer if checkpointer is not None else MemorySaver(),
        name="apollo_coordinator",
    )


def thread_config(thread_id: str) -> dict[str, Any]:
    """Run config selecting one conversation; reuse the same id for follow-up turns."""
    return {"configurable": {"thread_id": thread_id}}
