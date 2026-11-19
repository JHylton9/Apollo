"""Shared, lazily created resources for the tools (settings, vector store, retriever choice)."""

from __future__ import annotations

import dataclasses
import os
from functools import lru_cache
from pathlib import Path

from apollo.models import PipelineName, Settings
from apollo.retrieval import VectorStore
from apollo.retrieval.registry import RegistryStore
from apollo.retrieval.tables import RecordStore


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # APOLLO_ROOT lets the UI or tests run from another working directory.
    root = os.getenv("APOLLO_ROOT")
    settings = Settings.from_root(Path(root) if root else None)
    # APOLLO_ACTIONS_DIR sends action records elsewhere, e.g. evaluation runs keep their
    # audit trail with the evaluation report instead of mixing it into data/actions/.
    if actions_dir := os.getenv("APOLLO_ACTIONS_DIR"):
        settings = dataclasses.replace(settings, actions_dir=Path(actions_dir))
    return settings


@lru_cache(maxsize=1)
def get_store() -> VectorStore:
    # One Chroma client per process; opening it on every tool call would be slow.
    return VectorStore(get_settings().chroma_dir)


@lru_cache(maxsize=1)
def get_records() -> RecordStore:
    # Structured tables come from the Docling output saved during Phase 1 ingestion
    return RecordStore(get_settings().processed_dir / "docling")


@lru_cache(maxsize=1)
def get_registry() -> RegistryStore:
    return RegistryStore(get_settings().processed_dir / "docling")


def active_pipeline(default: PipelineName = "docling") -> PipelineName:
    """The collection a search tool uses.

    Each tool passes the pipeline that measurably works for its document (Phase 1
    benchmark): Docling for tables, baseline OCR for image-only posters. Setting
    APOLLO_RETRIEVER forces every tool onto one pipeline, for side-by-side demos.
    """
    value = os.getenv("APOLLO_RETRIEVER", default)
    if value not in ("baseline", "docling"):
        raise ValueError(f"APOLLO_RETRIEVER must be 'baseline' or 'docling', not {value!r}")
    return value  # type: ignore[return-value]
