from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from apollo.retrieval.registry import RegistryStore, parse_tip_lines, parse_wanted_persons

DOCLING_DIR = Path(__file__).parents[2] / "data" / "processed" / "docling"


def _doc(*items):
    """A stand-in for a DoclingDocument: (label, text, page) triples as text items."""
    return SimpleNamespace(
        texts=[
            SimpleNamespace(label=label, text=text, prov=[SimpleNamespace(page_no=page)])
            for label, text, page in items
        ]
    )


def test_entries_are_parsed_merged_and_ocr_slips_tolerated() -> None:
    doc = _doc(
        ("text", "DAVE EDWARDS Wanted for Murder LEROY GRAY Wanted for Assault at Common Law", 1),
        ("text", "CHRISTOPHER COMRIE OTHERWISE CALLED 'CHRIS' Wanted Far: Murder", 2),
        ("caption", "RAHEEM BROWN OTHERWISE CALLED 'BERGER'", 2),
        ("text", "Raheem Brown Wanted for Murder", 2),
        ("section_header", "JEVAUGHN CAMPBELL", 3),
        ("text", "Wanted for Murder &amp; Wounding with Intent", 3),
        ("text", "CONROY ROBINSON Wanted for Attempted Murder", 3),
        ("text", "Dave Edwards Wanted for Murder", 3),
    )
    people = {p.name: p for p in parse_wanted_persons(cast(Any, doc))}
    assert people["Dave Edwards"].pages == [1, 3]  # duplicates merged
    assert people["Leroy Gray"].offence == "Assault at Common Law"
    assert people["Christopher Comrie"].aliases == ["Chris"]  # "Wanted Far" read
    assert people["Raheem Brown"].aliases == ["Berger"]  # alias from a separate caption
    assert people["Jevaughn Campbell"].offence == "Murder and Wounding with Intent"
    assert people["Conroy Robinson"].offence == "Attempted Murder"  # not plain "Murder"


def test_tip_lines_are_found() -> None:
    doc = _doc(("text", "Police Emergency 119 Crime Stop 311 Tip Line 876-838-3589", 1))
    assert parse_tip_lines(cast(Any, doc)) == {
        "Police Emergency": "119",
        "Crime Stop": "311",
        "Tip Line": "876-838-3589",
    }


@pytest.mark.skipif(not DOCLING_DIR.exists(), reason="run `apollo ingest --pipeline docling` first")
def test_real_registry_matches_the_document() -> None:
    store = RegistryStore(DOCLING_DIR)
    murder = {p.name for p in store.wanted if p.offence.startswith("Murder")}
    assert murder == {
        "Christopher Comrie",
        "Dave Edwards",
        "Derrick Johnson",
        "Derrick Shaw",
        "Jermaine Richards",
        "Jevaughn Campbell",
        "Raheem Brown",
        "Samuel Brown",
    }
    # The spec's sample answer lists Leroy Gray, but the registry gives a different offence.
    assert "Leroy Gray" not in murder
    assert store.tip_lines["Tip Line"] == "876-838-3589"
