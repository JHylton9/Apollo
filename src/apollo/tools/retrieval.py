"""Semantic search tools over the Chroma collections, one per JCF document domain."""

from __future__ import annotations

from typing import Any

from langchain.tools import tool

from apollo.tools import _runtime

FINES_PDF = "JCF-Fines.pdf"
DIVISION_STATS_PDF = "JCF-Murder-Stats.pdf"
HISTORICAL_MURDERS_PDF = "JCF-Murder-Counts.pdf"
WANTED_PDF = "JCF-Wanted Persons.pdf"
MISSING_PDF = "JCF-Missing Persons.pdf"

Citation = dict[str, Any]


def _search(query: str, sources: list[str], top_k: int = 5) -> tuple[str, list[Citation]]:
    """Run a filtered search and return (text for the model, citations for the UI)."""
    if not query.strip():
        raise ValueError("The search query must not be empty.")
    pipeline = _runtime.active_pipeline()
    hits = _runtime.get_store().query(pipeline, query, top_k=top_k, sources=sources)
    if not hits:
        return f"No matching records were found in {', '.join(sources)}.", []

    blocks: list[str] = []
    citations: list[Citation] = []
    for rank, hit in enumerate(hits, start=1):
        page = f", page {hit.page}" if hit.page else ""
        blocks.append(f"[{rank}] {hit.source}{page} (relevance {hit.score:.2f})\n{hit.text}")
        citations.append(
            {
                "rank": rank,
                "source": hit.source,
                "page": hit.page,
                "score": round(hit.score, 4),
                "pipeline": pipeline,
            }
        )
    return "\n\n".join(blocks), citations


# Define strings for tools uing few shot technique
@tool(response_format="content_and_artifact")
def search_traffic_fines(query: str) -> tuple[str, list[Citation]]:
    """Search the official JCF traffic violation fine schedule.

    Use for fine amounts, demerit points and the Road Traffic Act section or regulation
    of a traffic offence. Put the offence wording and/or section number in the query,
    e.g. "driving without a driver's licence Section 20(4)".
    """
    return _search(query, [FINES_PDF])


@tool(response_format="content_and_artifact")
def search_division_crime_stats(query: str) -> tuple[str, list[Citation]]:
    """Search the JCF divisional crime statistics table comparing 2025 and 2026.

    Use for murders, shootings, rapes, robberies, break-ins and grand totals per police
    division (e.g. St. James, Westmoreland, St. Andrew North), including +/- and % change.
    """
    return _search(query, [DIVISION_STATS_PDF])


@tool(response_format="content_and_artifact")
def search_wanted_persons(query: str) -> tuple[str, list[Citation]]:
    """Search the JCF wanted persons registry: names, offences and citizen tip-line numbers."""
    return _search(query, [WANTED_PDF])


@tool(response_format="content_and_artifact")
def search_missing_persons(query: str) -> tuple[str, list[Citation]]:
    """Search the JCF missing persons alerts: names, descriptions and last-seen details."""
    return _search(query, [MISSING_PDF])


@tool(response_format="content_and_artifact")
def search_historical_murders(query: str) -> tuple[str, list[Citation]]:
    """Search the JCF historical national murder counts for Jamaica by year (1962 onward)."""
    return _search(query, [HISTORICAL_MURDERS_PDF])


# Defining a list the list of tools
RETRIEVAL_TOOLS = [
    search_traffic_fines,
    search_division_crime_stats,
    search_historical_murders,
    search_wanted_persons,
    search_missing_persons,
]
