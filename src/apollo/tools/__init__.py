"""LangChain tools that wrap the retrievers and high-risk actions (Phase 2).

Grouped by the specialist that will own them; the coordinator owns the actions.
"""

from apollo.tools.actions import ACTION_TOOLS, HIGH_RISK_TOOL_NAMES
from apollo.tools.records import (
    calculate,
    get_division_crime_stats,
    get_national_murder_counts,
    lookup_traffic_fine,
    rank_divisions_by_change,
)
from apollo.tools.retrieval import (
    search_division_crime_stats,
    search_historical_murders,
    search_missing_persons,
    search_traffic_fines,
    search_wanted_persons,
)

TRAFFIC_TOOLS = [lookup_traffic_fine, search_traffic_fines, calculate]
CRIME_STATS_TOOLS = [
    get_division_crime_stats,
    rank_divisions_by_change,
    get_national_murder_counts,
    search_division_crime_stats,
    search_historical_murders,
    calculate,
]
REGISTRY_TOOLS = [search_wanted_persons, search_missing_persons]

__all__ = [
    "ACTION_TOOLS",
    "CRIME_STATS_TOOLS",
    "HIGH_RISK_TOOL_NAMES",
    "REGISTRY_TOOLS",
    "TRAFFIC_TOOLS",
]