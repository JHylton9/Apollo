from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path


def stable_id(*parts: object) -> str:
    # Deterministic IDs make collection rebuilds reproducible.
    value = "|".join(str(part) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def clean_text(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def normalized(value: str) -> str:
    # Benchmark matching ignores punctuation and typography differences between parsers.
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = value.casefold().replace("$", " ")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def pdf_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.pdf"), key=lambda path: path.name.casefold())
