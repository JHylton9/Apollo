from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import chromadb
from chromadb.api.types import Where
from chromadb.errors import NotFoundError

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
        except NotFoundError:
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

    def query(
        self,
        pipeline: PipelineName,
        query: str,
        top_k: int = 5,
        *,
        sources: Sequence[str] | None = None,
    ) -> list[SearchHit]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        collection = self.client.get_collection(COLLECTIONS[pipeline])
        count = collection.count()
        if count == 0:
            return []

        where: Where | None = None
        if sources:
            where = (
                {"source": sources[0]} if len(sources) == 1 else {"source": {"$in": list(sources)}}
            )
        result = collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        documents_by_query = result["documents"]
        metadatas_by_query = result["metadatas"]
        distances_by_query = result["distances"]
        if not documents_by_query or not metadatas_by_query or not distances_by_query:
            raise RuntimeError("Chroma returned incomplete query results")

        documents = documents_by_query[0]
        metadatas = metadatas_by_query[0]
        distances = distances_by_query[0]
        if documents is None or metadatas is None or distances is None:
            raise RuntimeError("Chroma returned incomplete query results")

        # Cosine distance is converted to a more readable similarity score.
        hits = []
        for document, metadata, distance in zip(documents, metadatas, distances, strict=True):
            if metadata is None:
                raise RuntimeError("Chroma returned a result without metadata")
            page = metadata.get("page")
            hits.append(
                SearchHit(
                    text=document,
                    score=max(0.0, 1.0 - float(distance)),
                    source=str(metadata.get("source") or "unknown"),
                    page=int(page) if isinstance(page, (int, float)) else None,
                )
            )
        return hits

    def count(self, pipeline: PipelineName) -> int:
        try:
            return self.client.get_collection(COLLECTIONS[pipeline]).count()
        except NotFoundError:
            return 0
