"""Structured records rebuilt from Docling's parsed tables."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

from docling_core.types.doc.document import DoclingDocument

FINES_JSON = "JCF-Fines.json"
DIVISION_STATS_JSON = "JCF-Murder-Stats.json"
MURDER_COUNTS_JSON = "JCF-Murder-Counts.json"

_MONEY = re.compile(r"\$\s?([\d,]+)")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?%?")


@dataclass(frozen=True, slots=True)
class FineRecord:
    number: int
    offence: str
    fine: int
    points: int
    section: str
    page: int | None
    merged: bool = False
    merged_position: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class CategoryChange:
    year_2025: int
    year_2026: int

    @property
    def change(self) -> int:
        return self.year_2026 - self.year_2025

    @property
    def percent_change(self) -> float | None:
        if self.year_2025 == 0:
            return None
        return round(self.change / self.year_2025 * 100, 1)


@dataclass(frozen=True, slots=True)
class DivisionStats:
    division: str
    categories: dict[str, CategoryChange]  # only categories whose figures passed validation
    unverified: tuple[str, ...]  # categories Docling's table export left inconsistent


# Column order of the divisional matrix: 4 = 2025, 2026, +/-, %;  2 = 2025, 2026 only.
STAT_CATEGORIES: tuple[tuple[str, int], ...] = (
    ("murder", 4),
    ("shooting", 4),
    ("persons_injured", 2),
    ("rape", 4),
    ("robbery", 4),
    ("break_in", 4),
    ("grand_total", 4),
)


def load_document(path: Path) -> DoclingDocument:
    return DoclingDocument.model_validate(json.loads(path.read_text(encoding="utf-8")))


def normalize_section(value: str) -> str:
    """'s.20 (4)', 'Section 20(4)' and '20(4)' all become '20(4)'."""
    value = value.casefold()
    value = re.sub(r"\b(section|sec|s|regulation|reg|r)\b\.?", " ", value)
    return re.sub(r"\s+", "", value)


def _cells(table: Any, doc: DoclingDocument) -> list[list[str]]:
    frame = table.export_to_dataframe(doc=doc)
    rows = [[str(value).strip() for value in row] for row in frame.itertuples(index=False)]
    # Continuation tables have numeric column labels and sometimes repeat the header as row 0.
    return [row for row in rows if row and row[0].upper() not in {"CONS#", "YEAR", "DIVISION"}]


def _page(table: Any) -> int | None:
    return table.prov[0].page_no if getattr(table, "prov", None) else None


def _split_fine_row(row: list[str], page: int | None) -> list[FineRecord] | None:
    """Turn one table row into records, or return None if it cannot be read unambiguously.

    Docling sometimes merges two neighbouring rows into one, e.g. numbers "88 89", fines
    "$15,000 $5,000", sections "Section 7(3) Section 71(2)(f)". When every column holds the
    same number of values we can still pair them up; otherwise the row is left out.
    """
    numbers = re.findall(r"\d+", row[0])
    fines = [int(value.replace(",", "")) for value in _MONEY.findall(row[2])]
    points = [int(value) for value in re.findall(r"\d+", row[3])]
    sections = [
        part.strip() for part in re.split(r"\s+(?=(?:Section|Regulation)\b)", row[5]) if part
    ]
    count = len(numbers)
    if count == 0 or not (len(fines) == len(sections) == count):
        return None
    if len(points) != count:
        points = [0] * count if not points else points
        if len(points) != count:
            return None
    return [
        FineRecord(
            number=int(numbers[i]),
            offence=row[1],
            fine=fines[i],
            points=points[i],
            section=sections[i],
            page=page,
            merged=count > 1,
            merged_position=(i + 1, count) if count > 1 else None,
        )
        for i in range(count)
    ]


def parse_fine_schedule(doc: DoclingDocument) -> tuple[list[FineRecord], list[list[str]]]:
    """Return (records, unreadable rows). Unreadable rows are kept for the Phase 1/2 report."""
    records: list[FineRecord] = []
    unreadable: list[list[str]] = []
    for table in doc.tables:
        for row in _cells(table, doc):
            if len(row) < 6:
                continue
            parsed = _split_fine_row(row, _page(table))
            if parsed is None:
                unreadable.append(row)
            else:
                records.extend(parsed)
    return records, unreadable


def _as_change(tokens: list[str]) -> CategoryChange | None:
    """Accept (2025, 2026, +/-, %) only if the arithmetic agrees with the printed values."""
    first, second, delta, percent = tokens
    if "%" in first + second + delta or not percent.endswith("%"):
        return None
    a, b, d, p = (float(token.rstrip("%")) for token in tokens)
    # Docling occasionally swaps the two year cells of a merged column; the +/- settles it.
    for old, new in ((a, b), (b, a)):
        if new - old == d and (old == 0 or abs(d / old * 100 - p) <= 0.15):
            return CategoryChange(int(old), int(new))
    return None


def _parse_division_row(tokens: list[str]) -> tuple[dict[str, CategoryChange], list[str]]:
    found: dict[str, CategoryChange] = {}
    position = 0
    for name, width in STAT_CATEGORIES:
        if name == "grand_total":
            # The grand total is always the final four values, even if earlier cells shifted.
            change = _as_change(tokens[-4:]) if len(tokens) >= 4 else None
        elif width == 2:
            # No +/- column to check, so accept the pair only where the next category's
            # four values validate straight after it (i.e. the row is still aligned).
            change = None
            for start in range(position, min(position + 3, len(tokens) - 5)):
                pair = tokens[start : start + 2]
                if any("%" in token for token in pair):
                    continue
                if _as_change(tokens[start + 2 : start + 6]):
                    change = CategoryChange(int(float(pair[0])), int(float(pair[1])))
                    position = start + 2
                    break
        else:
            change = None
            for start in range(position, min(position + 3, len(tokens) - 3)):
                change = _as_change(tokens[start : start + 4])
                if change:
                    position = start + 4
                    break
        if change:
            found[name] = change
    missing = [name for name, _ in STAT_CATEGORIES if name not in found]
    return found, missing


def parse_division_stats(doc: DoclingDocument) -> list[DivisionStats]:
    divisions: list[DivisionStats] = []
    for table in doc.tables:
        for row in _cells(table, doc):
            name = row[0]
            tokens = _NUMBER.findall(" ".join(row[1:]))
            if not name or not tokens:
                continue
            found, missing = _parse_division_row(tokens)
            divisions.append(DivisionStats(name, found, tuple(missing)))
    return divisions


def parse_murder_counts(doc: DoclingDocument) -> dict[int, int]:
    counts: dict[int, int] = {}
    for table in doc.tables:
        for row in _cells(table, doc):
            if len(row) >= 2 and row[0].isdigit():
                counts[int(row[0])] = round(float(row[1].replace(",", "")))
    return counts


class RecordStore:
    """Lazy access to the structured JCF tables saved by `apollo ingest --pipeline docling`."""

    def __init__(self, docling_dir: Path) -> None:
        self.docling_dir = docling_dir

    def _document(self, name: str) -> DoclingDocument:
        path = self.docling_dir / name
        if not path.exists():
            raise FileNotFoundError(
                f"{path} is missing; run `uv run apollo ingest --pipeline docling` first."
            )
        return load_document(path)

    @cached_property
    def _fine_table(self) -> tuple[list[FineRecord], list[list[str]]]:
        return parse_fine_schedule(self._document(FINES_JSON))

    @property
    def fines(self) -> list[FineRecord]:
        return self._fine_table[0]

    @property
    def unreadable_fine_rows(self) -> list[list[str]]:
        return self._fine_table[1]

    @cached_property
    def divisions(self) -> list[DivisionStats]:
        return parse_division_stats(self._document(DIVISION_STATS_JSON))

    @cached_property
    def murder_counts(self) -> dict[int, int]:
        return parse_murder_counts(self._document(MURDER_COUNTS_JSON))
