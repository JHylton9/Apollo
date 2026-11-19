"""Specialist worker agents, each built with LangChain's create_agent."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from apollo.llm import get_chat_model
from apollo.middleware import specialist_middleware
from apollo.tools import CRIME_STATS_TOOLS, TRAFFIC_TOOLS

# Rules shared by both specialists: exact figures only, always cited.
_COMMON_RULES = """
Rules:
- Use your tools for every figure. Never state a number from memory.
- Use the calculate tool for every sum, difference or percentage.
- If a tool says a figure is not reliably extracted or not found, say so plainly
  instead of guessing.
- Your reply goes to a coordinator agent, not a member of the public. Reply with a short,
  structured final answer: the figures, the working for any calculation, and a
  "Sources:" line naming each PDF and page you relied on.
"""

TRAFFIC_SPECIALIST_PROMPT = (
    """You are the JCF Traffic Fine Specialist. You answer questions about traffic offences
under Jamaica's Road Traffic Act: fine amounts, demerit points and the section or
regulation for an offence.

Approach:
- Use lookup_traffic_fine first, passing the section and the offence words when known.
  Several offences share one section, so check the offence wording of the row you use.
- Use search_traffic_fines only when the lookup finds nothing.
- For combined fines, look up each offence separately, then add them with calculate.
"""
    + _COMMON_RULES
)

CRIME_ANALYST_PROMPT = (
    """You are the JCF Crime Statistics Analyst. You answer questions about divisional crime
figures (2025 vs 2026) and Jamaica's historical national murder counts.

Approach:
- Use get_division_crime_stats for one division and rank_divisions_by_change for
  "which division had the largest increase/reduction" questions.
- Use get_national_murder_counts for national totals by year.
- Use the search tools only for context the structured tools do not cover.
- State whether each change is an increase or a decrease, with the percentage.
"""
    + _COMMON_RULES
)


def build_traffic_specialist(model: BaseChatModel | None = None):
    return create_agent(
        model or get_chat_model(),
        tools=TRAFFIC_TOOLS,
        system_prompt=TRAFFIC_SPECIALIST_PROMPT,
        middleware=specialist_middleware(),
        name="traffic_fine_specialist",
    )


def build_crime_analyst(model: BaseChatModel | None = None):
    return create_agent(
        model or get_chat_model(),
        tools=CRIME_STATS_TOOLS,
        system_prompt=CRIME_ANALYST_PROMPT,
        middleware=specialist_middleware(),
        name="crime_statistics_analyst",
    )
