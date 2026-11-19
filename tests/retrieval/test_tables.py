from pathlib import Path

import pytest

from apollo.retrieval.tables import (
    CategoryChange,
    RecordStore,
    _as_change,
    _parse_division_row,
    _split_fine_row,
    normalize_section,
)

DOCLING_DIR = Path(__file__).parents[2] / "data" / "processed" / "docling"


def test_section_formats_are_normalized() -> None:
    assert normalize_section("Section 20(4)") == "20(4)"
    assert normalize_section("s. 20 (4)") == "20(4)"
    assert normalize_section("Regulation 180(2)") == "180(2)"


def test_merged_fine_rows_are_split() -> None:
    # Real row from JCF-Fines.pdf page 2, where Docling merged two table rows.
    row = [
        "88 89",
        "No Valid Certificate Of Fitness No Warning Devices",
        "$15,000 $5,000",
        "0 2",
        "N N",
        "Section 7(3) Section 71(2)(f)",
    ]
    result = _split_fine_row(row, page=2)
    assert result is not None
    first, second = result
    assert (first.number, first.fine, first.points, first.section) == (88, 15000, 0, "Section 7(3)")
    assert (second.number, second.fine, second.section) == (89, 5000, "Section 71(2)(f)")
    assert first.merged and second.merged
    assert (first.merged_position, second.merged_position) == ((1, 2), (2, 2))


def test_ambiguous_fine_rows_are_rejected() -> None:
    # Two row numbers but only one fine: pairing them would be a guess.
    row = ["24 25", "Driving closer than 50 meters", "$9,000", "3", "N", "Section 57(5) (e)"]
    assert _split_fine_row(row, page=1) is None


def test_change_is_validated_and_swapped_cells_repaired() -> None:
    assert _as_change(["46", "54", "8", "17.4%"]) == CategoryChange(46, 54)
    # Docling exported Westmoreland's grand total as "108 143" although +/- is -35.
    assert _as_change(["108", "143", "-35", "-24.5%"]) == CategoryChange(143, 108)
    assert _as_change(["46", "54", "9", "17.4%"]) is None


def test_division_row_keeps_only_verified_categories() -> None:
    tokens: list[str] = [
        str(token)
        for token in (
            "16 9 -7 -43.8% 14 10 -4 -28.6% 7 4 19 12 -7 -36.8% "
            "7 11 4 57.1% 46 -195 60 836 14 30.4% 102 102 0 0.0%"
        ).split()
    ]
    found, missing = _parse_division_row(tokens)
    assert found["murder"] == CategoryChange(16, 9)
    assert found["grand_total"] == CategoryChange(102, 102)
    assert "break_in" in missing


@pytest.mark.skipif(not DOCLING_DIR.exists(), reason="run `apollo ingest --pipeline docling` first")
def test_spec_figures_from_real_docling_output() -> None:
    store = RecordStore(DOCLING_DIR)
    by_section = {}
    for record in store.fines:
        by_section.setdefault(normalize_section(record.section), []).append(record)
    assert {r.fine for r in by_section["20(4)"]} >= {40000}
    assert {r.fine for r in by_section["83(3)"]} == {10000}
    assert any(r.fine == 15000 and "Fitness" in r.offence for r in by_section["7(3)"])

    divisions = {d.division: d for d in store.divisions}
    assert divisions["St. James"].categories["murder"] == CategoryChange(46, 54)
    assert divisions["St. Andrew North"].categories["grand_total"].percent_change == -59.6

    assert store.murder_counts[1980] == 889
    assert store.murder_counts[2024] == 1147


def test_unvalidated_pair_is_not_trusted() -> None:
    tokens: list[str] = [
        str(token)
        for token in (
            "50 33 -17 -34.0% 30 13 -17 -56.7% 11 17 15 -2 -11.8% "
            "52 28 0.0% 24 -24 -46.2% 68 80 12 17.6% 217 169 -48 -22.1%"
        ).split()
    ]
    found, missing = _parse_division_row(tokens)
    assert "persons_injured" in missing
    assert found["rape"] == CategoryChange(17, 15)
