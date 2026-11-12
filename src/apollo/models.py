from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

PipelineName = Literal["baseline", "docling"]


@dataclass(frozen=True, slots=True)
class Chunk:
    """A retrievable unit with citation-ready provenance."""

    id: str
    text: str
    source: str
    pipeline: PipelineName
    page: int | None = None
    chunk_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def chroma_metadata(self) -> dict[str, str | int | float | bool]:
        # Chroma accepts only scalar metadata values, so nested parser data stays out.
        data: dict[str, str | int | float | bool] = {
            "source": self.source,
            "pipeline": self.pipeline,
            "chunk_index": self.chunk_index,
        }
        if self.page is not None:
            data["page"] = self.page
        for key, value in self.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                data[key] = value
        return data


@dataclass(frozen=True, slots=True)
class SearchHit:
    text: str
    score: float
    source: str
    page: int | None


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    id: str
    question: str
    expected_source: str
    evidence_groups: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class Settings:
    raw_dir: Path
    processed_dir: Path
    chroma_dir: Path
    reports_dir: Path
    benchmark_file: Path
    chunk_size: int = 1000
    chunk_overlap: int = 200

    @classmethod
    def from_root(cls, root: Path | None = None) -> Settings:
        resolved = (root or Path.cwd()).resolve()
        return cls(
            raw_dir=resolved / "data" / "raw",
            processed_dir=resolved / "data" / "processed",
            chroma_dir=resolved / "data" / "chroma",
            reports_dir=resolved / "reports",
            benchmark_file=resolved / "benchmarks" / "phase1_queries.json",
        )
