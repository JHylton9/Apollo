from pathlib import Path
from typing import Any

import pytest

from apollo.retrieval.store import VectorStore


class FakeCollection:
    def __init__(self) -> None:
        self.query_arguments: dict[str, Any] | None = None

    def count(self) -> int:
        return 2

    def query(self, **kwargs: Any) -> dict[str, list[list[Any]]]:
        self.query_arguments = kwargs
        return {
            "documents": [["A matching chunk"]],
            "metadatas": [[{"source": "Wanted Persons.pdf", "page": 2}]],
            "distances": [[0.25]],
        }


class FakeClient:
    def __init__(self, collection: FakeCollection) -> None:
        self.collection = collection

    def get_collection(self, _name: str) -> FakeCollection:
        return self.collection


def test_query_applies_source_filter_and_returns_hits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = VectorStore(tmp_path)
    collection = FakeCollection()
    monkeypatch.setattr(store, "client", FakeClient(collection))

    hits = store.query(
        "baseline",
        "question",
        sources=("Wanted Persons.pdf", "Missing Persons.pdf"),
    )

    assert collection.query_arguments is not None
    assert collection.query_arguments["where"] == {
        "source": {"$in": ["Wanted Persons.pdf", "Missing Persons.pdf"]}
    }
    assert hits[0].text == "A matching chunk"
    assert hits[0].score == 0.75
    assert hits[0].source == "Wanted Persons.pdf"
    assert hits[0].page == 2
