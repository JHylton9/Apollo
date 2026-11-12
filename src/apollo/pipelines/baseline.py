from __future__ import annotations

from pathlib import Path

import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from apollo.models import Chunk
from apollo.ocr import PageOCR
from apollo.text import clean_text, stable_id


class BaselinePipeline:
    """Standard page text/OCR followed by overlapping character chunks."""

    name = "baseline"

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
            add_start_index=True,
        )
        self.ocr = PageOCR()

    def ingest(self, path: Path) -> list[Chunk]:
        reader = PdfReader(path)
        rendered = pymupdf.open(path)
        chunks: list[Chunk] = []
        chunk_index = 0
        try:
            for page_index, page in enumerate(reader.pages):
                extracted = clean_text(page.extract_text() or "")
                use_ocr = self.ocr.needed(rendered[page_index], extracted)
                ocr_text = self.ocr.extract(rendered[page_index]) if use_ocr else ""
                # Prefer OCR only when it recovers substantially more page content.
                page_text = self._select_text(extracted, ocr_text)
                if not page_text:
                    continue
                documents = self.splitter.create_documents(
                    [page_text],
                    metadatas=[{"page": page_index + 1, "ocr_used": use_ocr}],
                )
                for document in documents:
                    body = clean_text(document.page_content)
                    if not body:
                        continue
                    # Source and page labels improve retrieval and remain available for citations.
                    text = f"Source: {path.stem}\nPage: {page_index + 1}\n{body}"
                    start = int(document.metadata.get("start_index", 0))
                    chunks.append(
                        Chunk(
                            id=stable_id(self.name, path.name, page_index + 1, start, text),
                            text=text,
                            source=path.name,
                            pipeline="baseline",
                            page=page_index + 1,
                            chunk_index=chunk_index,
                            metadata={"ocr_used": use_ocr, "start_index": start},
                        )
                    )
                    chunk_index += 1
        finally:
            rendered.close()
        return chunks

    @staticmethod
    def _select_text(extracted: str, ocr_text: str) -> str:
        if len(ocr_text) > len(extracted) * 1.15:
            return ocr_text
        return extracted
