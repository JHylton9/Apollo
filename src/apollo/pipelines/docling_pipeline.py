from __future__ import annotations

from pathlib import Path
from typing import Any

from apollo.models import Chunk
from apollo.text import clean_text, stable_id


class DoclingPipeline:
    """Layout-aware conversion and hierarchical hybrid chunking with Docling."""

    name = "docling"

    def __init__(self) -> None:
        self._converter = None
        self._chunker = None

    def ingest(self, path: Path) -> tuple[list[Chunk], dict[str, Any]]:
        from docling.chunking import HybridChunker
        from docling.document_converter import DocumentConverter
        from transformers.utils import logging as transformers_logging

        # Token counting on wide tables can emit a false inference-length warning.
        transformers_logging.set_verbosity_error()
        self._converter = self._converter or DocumentConverter()
        # Hybrid chunking retains document hierarchy and repeats table headers.
        self._chunker = self._chunker or HybridChunker(repeat_table_header=True)
        result = self._converter.convert(path)
        document = result.document
        chunks: list[Chunk] = []
        for index, raw_chunk in enumerate(self._chunker.chunk(dl_doc=document)):
            body = clean_text(self._chunker.contextualize(chunk=raw_chunk))
            if not body:
                continue
            text = f"Source: {path.stem}\n{body}"
            meta = self._metadata(raw_chunk)
            page = self._page_number(meta)
            chunks.append(
                Chunk(
                    id=stable_id(self.name, path.name, index, text),
                    text=text,
                    source=path.name,
                    pipeline="docling",
                    page=page,
                    chunk_index=index,
                )
            )
        artifact = {
            "source": path.name,
            "markdown": document.export_to_markdown(),
            "document": document.export_to_dict(),
            "chunks": len(chunks),
        }
        try:
            result.input.release()
        except Exception:
            pass
        return chunks, artifact

    @staticmethod
    def _metadata(chunk: Any) -> dict[str, Any]:
        meta = getattr(chunk, "meta", None)
        if meta is None:
            return {}
        if hasattr(meta, "export_json_dict"):
            return meta.export_json_dict()
        if hasattr(meta, "model_dump"):
            return meta.model_dump(mode="json")
        return {}

    @classmethod
    def _page_number(cls, value: Any) -> int | None:
        # Provenance is nested differently for text and table chunks.
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"page", "page_no", "page_number"} and isinstance(item, int):
                    return item
                found = cls._page_number(item)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = cls._page_number(item)
                if found is not None:
                    return found
        return None
