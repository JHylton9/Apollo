from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import chromadb

from apollo.models import Chunk, PipelineName, SearchHit

COLLECTIONS: dict[PipelineName, str] = {
    "baseline": "jcf_baseline_rag",
    "docling": "jcf_docling_rag",
}


class VectorStore:
    def __init__(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(path))

    def rebuild(self, pipeline: PipelineName, chunks: Iterable[Chunk]) -> int:
        name = COLLECTIONS[pipeline]
        # Recreate the selected collection so old chunks cannot leak into a benchmark.
        try:
            self.client.delete_collection(name)
        except Exception:
            pass
        collection = self.client.get_or_create_collection(
            name=name,
            metadata={"pipeline": pipeline, "hnsw:space": "cosine"},
        )
        records = list(chunks)
        batch_size = min(self.client.get_max_batch_size(), 250)
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            collection.add(
                ids=[item.id for item in batch],
                documents=[item.text for item in batch],
                metadatas=[item.chroma_metadata() for item in batch],
            )
        return collection.count()

    def query(self, pipeline: PipelineName, query: str, top_k: int = 5) -> list[SearchHit]:
        collection = self.client.get_collection(COLLECTIONS[pipeline])
        count = collection.count()
        if count == 0:
            return []
        result = collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]
        # Cosine distance is converted to a more readable similarity score.
        return [
            SearchHit(
                text=document,
                score=max(0.0, 1.0 - float(distance)),
                source=str(metadata.get("source", "unknown")),
                page=int(metadata["page"]) if "page" in metadata else None,
            )
            for document, metadata, distance in zip(documents, metadatas, distances, strict=True)
        ]

    def count(self, pipeline: PipelineName) -> int:
        try:
            return self.client.get_collection(COLLECTIONS[pipeline]).count()
        except Exception:
            return 0
