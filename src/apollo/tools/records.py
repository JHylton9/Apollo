"""Exact-lookup tools over the structured Docling tables, plus a safe calculator."""

from __future__ import annotations

import ast
import operator
import re
from typing import Any, Literal

from langchain.tools import tool

from apollo.retrieval.tables import DivisionStats, FineRecord, normalize_section
from apollo.tools import _runtime

FINES_PDF = "JCF-Fines.pdf"
DIVISION_STATS_PDF = "JCF-Murder-Stats.pdf"
MURDER_COUNTS_PDF = "JCF-Murder-Counts.pdf"
WANTED_PDF = "JCF-Wanted Persons.pdf"

Category = Literal[
    "murder", "shooting", "persons_injured", "rape", "robbery", "break_in", "grand_total"
]
Citation = dict[str, Any]

# A section looks like "20(4)", "54(4)(a)(ii)" or "123" once "Section"/"Regulation" is removed.
_SECTION_SHAPE = re.compile(r"^\d+[a-z]?(\([0-9a-z]+\))*$")
_WORD = re.compile(r"[a-z0-9]+")
_ORDINALS = {1: "first", 2: "second", 3: "third", 4: "fourth"}


def _cite(source: str, page: int | None) -> Citation:
    return {"source": source, "page": page, "pipeline": "docling-table"}


def _format_fine(record: FineRecord) -> str:
    line = (
        f"No. {record.number} | {record.offence} | fine ${record.fine:,} | "
        f"{record.points} demerit points | {record.section} | {FINES_PDF} page {record.page}"
    )
    if record.merged_position:
        entry, total = record.merged_position
        # Columns were split in order, so entry N is the N-th offence named in the text.
        line += (
            f" | note: Docling merged {total} schedule rows into one; this is entry {entry} of"
            f" {total}, so it is the offence named {_ORDINALS[entry]} in the combined text"
        )
    return line


def _offence_matches(records: list[FineRecord], offence: str) -> list[FineRecord]:
    wanted = set(_WORD.findall(offence.casefold()))
    scored = []
    for record in records:
        overlap = len(wanted & set(_WORD.findall(record.offence.casefold())))
        if overlap:
            scored.append((overlap, record))
    scored.sort(key=lambda item: (-item[0], item[1].number))
    best = scored[0][0] if scored else 0
    # Keep only the closest matches so the model is not handed half the schedule.
    return [record for score, record in scored if score >= max(1, best - 1)][:5]


@tool(response_format="content_and_artifact")
def lookup_traffic_fine(
    section: str | None = None, offence: str | None = None
) -> tuple[str, list[Citation]]:
    """Look up exact fines and demerit points in the JCF traffic fine schedule.

    Give a Road Traffic Act section or regulation (e.g. "20(4)" or "Section 52(2)(a)"),
    a few words of the offence (e.g. "without driver's licence"), or both. Several offences
    can share one section, so pass the offence words too when you know them.
    Always prefer this tool over search for fine amounts and points.
    """
    if not section and not offence:
        raise ValueError("Provide a section number, offence words, or both.")
    records = _runtime.get_records().fines

    if section:
        key = normalize_section(section)
        if not _SECTION_SHAPE.match(key):
            raise ValueError(
                f"'{section}' is not a valid Road Traffic Act section or regulation code. "
                "Expected a form like '20(4)' or 'Section 54(4)(a)(ii)'."
            )
        records = [r for r in records if normalize_section(r.section) == key]
        if not records:
            return (
                f"No readable row for section {section} was found in the structured fine table. "
                "Docling could not read a few rows cleanly, so try search_traffic_fines.",
                [],
            )
    if offence:
        narrowed = _offence_matches(records, offence)
        # With a section, keep all its rows if the words match none; without one, words decide.
        records = (narrowed or records) if section else narrowed
        if not records:
            return (
                f"No offence matching '{offence}' was found; try search_traffic_fines.",
                [],
            )

    lines = [_format_fine(record) for record in records]
    citations = [_cite(FINES_PDF, record.page) for record in records]
    return "\n".join(lines), citations


def _division_key(name: str) -> str:
    return " ".join(_WORD.findall(name.casefold()))


def _find_division(name: str) -> DivisionStats:
    divisions = _runtime.get_records().divisions
    key = _division_key(name)
    for division in divisions:
        if _division_key(division.division) == key:
            return division
    known = ", ".join(d.division for d in divisions)
    raise ValueError(f"Unknown division '{name}'. Known divisions: {known}.")


def _format_category(name: str, division: DivisionStats) -> str:
    change = division.categories[name]
    percent = "n/a" if change.percent_change is None else f"{change.percent_change:+.1f}%"
    return (
        f"{name.replace('_', ' ')}: 2025 = {change.year_2025}, 2026 = {change.year_2026}, "
        f"change = {change.change:+d} ({percent})"
    )


@tool(response_format="content_and_artifact")
def get_division_crime_stats(division: str) -> tuple[str, list[Citation]]:
    """Get verified 2025 vs 2026 crime figures for one JCF police division.

    Covers murder, shooting, persons injured, rape, robbery, break-in and grand total, with
    the change and percentage change. Use "Grand Total" for the national row.
    """
    stats = _find_division(division)
    lines = [f"Division: {stats.division} ({DIVISION_STATS_PDF} page 1)"]
    lines += [_format_category(name, stats) for name in stats.categories]
    if stats.unverified:
        lines.append(
            "Not reliably extracted (do not state these figures): " + ", ".join(stats.unverified)
        )
    return "\n".join(lines), [_cite(DIVISION_STATS_PDF, 1)]


@tool(response_format="content_and_artifact")
def rank_divisions_by_change(
    category: Category = "grand_total",
    order: Literal["largest_reduction", "largest_increase"] = "largest_reduction",
    limit: int = 5,
) -> tuple[str, list[Citation]]:
    """Rank JCF divisions by percentage change in a crime category from 2025 to 2026.

    Use for questions such as "which division had the highest percentage reduction in
    total major crimes" (category="grand_total", order="largest_reduction").
    """
    divisions = [
        d
        for d in _runtime.get_records().divisions
        if d.division != "Grand Total"
        and category in d.categories
        and d.categories[category].percent_change is not None
    ]
    divisions.sort(
        key=lambda d: d.categories[category].percent_change or 0.0,
        reverse=order == "largest_increase",
    )
    limit = max(1, min(limit, 20))
    lines = [
        f"Divisions ranked by {order.replace('_', ' ')} in {category.replace('_', ' ')} "
        f"({DIVISION_STATS_PDF} page 1):"
    ]
    lines += [
        f"{rank}. {d.division} - {_format_category(category, d)}"
        for rank, d in enumerate(divisions[:limit], start=1)
    ]
    return "\n".join(lines), [_cite(DIVISION_STATS_PDF, 1)]


@tool(response_format="content_and_artifact")
def get_national_murder_counts(years: list[int]) -> tuple[str, list[Citation]]:
    """Get Jamaica's official national murder totals for specific years (1962 onward)."""
    if not years:
        raise ValueError("Provide at least one year.")
    counts = _runtime.get_records().murder_counts
    lines = [f"National murder totals ({MURDER_COUNTS_PDF}):"]
    lines += [f"{year}: {counts[year]:,} murders" for year in years if year in counts]
    missing = [str(year) for year in years if year not in counts]
    if missing:
        lines.append(f"No figure in {MURDER_COUNTS_PDF} for: {', '.join(missing)}")
    return "\n".join(lines), [_cite(MURDER_COUNTS_PDF, None)]


@tool(response_format="content_and_artifact")
def list_wanted_persons(offence: str | None = None) -> tuple[str, list[Citation]]:
    """List people in the JCF wanted persons registry, with aliases and offences, plus the
    official citizen tip-line numbers.

    Pass an offence such as "Murder" to filter. "Murder" includes people wanted for murder
    together with another offence, but not "Attempted Murder", which is a separate offence.
    """
    registry = _runtime.get_registry()
    people = registry.wanted
    if offence:
        wanted = " ".join(_WORD.findall(offence.casefold()))
        people = [
            p
            for p in people
            if " ".join(_WORD.findall(p.offence.casefold())) == wanted
            or " ".join(_WORD.findall(p.offence.casefold())).startswith(wanted + " and ")
        ]
    label = f"wanted for {offence}" if offence else "in the wanted persons registry"
    lines = [f"{len(people)} people {label} ({WANTED_PDF}):"]
    for person in people:
        alias = f" (also called {', '.join(person.aliases)})" if person.aliases else ""
        pages = ", ".join(str(page) for page in person.pages)
        lines.append(f"- {person.name}{alias}: wanted for {person.offence} (page {pages})")
    if registry.tip_lines:
        numbers = "; ".join(f"{name} {number}" for name, number in registry.tip_lines.items())
        lines.append(f"Citizen reporting numbers: {numbers}")
    pages = sorted({page for person in people for page in person.pages})
    return "\n".join(lines), [_cite(WANTED_PDF, page) for page in pages]


_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluate(node: ast.AST) -> float:
    # Walk the parsed expression ourselves: eval() would run arbitrary code.
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.operand))
    raise ValueError("Only numbers, + - * / ** and parentheses are allowed.")


@tool
def calculate(expression: str) -> str:
    """Evaluate an arithmetic expression exactly, e.g. "40000 + 10000" or "(54 - 46) / 46 * 100".

    Use this for every sum, difference or percentage instead of calculating mentally.
    """
    cleaned = expression.replace(",", "").replace("$", "").strip()
    try:
        result = _evaluate(ast.parse(cleaned, mode="eval"))
    except ZeroDivisionError as error:
        raise ValueError("Division by zero.") from error
    except SyntaxError as error:
        raise ValueError(f"'{expression}' is not a valid arithmetic expression.") from error
    return f"{expression} = {round(result, 4):,}"


RECORD_TOOLS = [
    lookup_traffic_fine,
    get_division_crime_stats,
    rank_divisions_by_change,
    get_national_murder_counts,
    calculate,
    list_wanted_persons,
]
