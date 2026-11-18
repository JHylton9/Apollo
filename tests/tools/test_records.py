from types import SimpleNamespace

import pytest

from apollo.retrieval.tables import CategoryChange, DivisionStats, FineRecord
from apollo.tools import _runtime, records

FINES = [
    FineRecord(1, "Aid And Abet No Driver's Licence or Permit", 15000, 0, "Section 20(4)", 1),
    FineRecord(67, "Failing To Produce Driver's Licence/Permit", 2000, 0, "Section 20(4)", 2),
    FineRecord(
        115,
        "Operating Motor Vehicle Without Driver's Licence/Permit",
        40000,
        14,
        "Section 20(4)",
        3,
    ),
    FineRecord(
        72, "Failing To Yield Right Of Way at Pedestrian Crossing", 10000, 4, "Section 83(3)", 2
    ),
]
DIVISIONS = [
    DivisionStats("St. James", {"grand_total": CategoryChange(205, 223)}, ()),
    DivisionStats("St. Andrew North", {"grand_total": CategoryChange(250, 101)}, ()),
    DivisionStats("St. Ann", {"murder": CategoryChange(50, 33)}, ("robbery",)),
    DivisionStats("Grand Total", {"grand_total": CategoryChange(3061, 2419)}, ()),
]


@pytest.fixture(autouse=True)
def fake_records(monkeypatch):
    store = SimpleNamespace(fines=FINES, divisions=DIVISIONS, murder_counts={1980: 889})
    monkeypatch.setattr(_runtime, "get_records", lambda: store)


def _content(tool, args):
    return tool.invoke({"type": "tool_call", "id": "t1", "name": tool.name, "args": args}).content


def test_section_and_offence_pick_the_right_row() -> None:
    text = _content(
        records.lookup_traffic_fine,
        {"section": "20(4)", "offence": "driving without driver's licence"},
    )
    assert text.splitlines()[0].startswith("No. 115")
    assert "$40,000" in text and "14 demerit points" in text


def test_invalid_section_code_raises_value_error() -> None:
    # Spec test case: ToolErrorMiddleware (Module 4) will catch this.
    with pytest.raises(ValueError):
        records.lookup_traffic_fine.invoke({"section": "invalid_section_code_9999"})


def test_unknown_but_valid_section_suggests_search() -> None:
    assert "search_traffic_fines" in _content(records.lookup_traffic_fine, {"section": "999(9)"})


def test_division_lookup_hides_unverified_figures() -> None:
    text = _content(records.get_division_crime_stats, {"division": "st ann"})
    assert "murder: 2025 = 50, 2026 = 33" in text
    assert "Not reliably extracted" in text and "robbery" in text


def test_unknown_division_raises() -> None:
    with pytest.raises(ValueError):
        records.get_division_crime_stats.invoke({"division": "Atlantis"})


def test_ranking_excludes_national_total() -> None:
    text = _content(records.rank_divisions_by_change, {"category": "grand_total", "limit": 2})
    assert "1. St. Andrew North" in text and "-59.6%" in text
    assert "Grand Total -" not in text


def test_murder_counts_report_missing_years() -> None:
    text = _content(records.get_national_murder_counts, {"years": [1980, 1950]})
    assert "1980: 889 murders" in text and "1950" in text


def test_calculator_is_exact_and_safe() -> None:
    assert records.calculate.invoke({"expression": "40,000 + 10,000"}).endswith("= 50,000")
    with pytest.raises(ValueError):
        records.calculate.invoke({"expression": "__import__('os').system('ls')"})