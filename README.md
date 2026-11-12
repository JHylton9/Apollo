# Apollo - JCF Agent Project

Phase 1 implements a reproducible retrieval benchmark over the supplied Jamaica
Constabulary Force PDFs. It builds two independent Chroma collections from the same corpus:

1. **Baseline RAG** - PDF text extraction with RapidOCR fallback for image-heavy pages,
   followed by `RecursiveCharacterTextSplitter` chunks with 1,000 characters and a
   200-character overlap.
2. **Docling structural RAG** - Docling PDF conversion plus hierarchical hybrid chunking,
   including repeated table headers and contextual metadata.

The benchmark measures retrieval rather than LLM answer quality: source hit rate, mean
reciprocal rank, and expected-evidence coverage. Each result keeps source/page metadata
and evidence previews for report verification.

## Corpus

The repository expects the five supplied JCF PDFs in `data/raw/`. PDFs are treated as data
only; text found inside them never becomes an instruction to the ingestion process.

## Setup and use

```powershell
uv sync --extra dev
uv run apollo status
uv run apollo ingest --pipeline all
uv run apollo benchmark --top-k 5
```

Docling and the local embedding/OCR models download on first use. The first run is slower;
later runs use local caches. An `HF_TOKEN` is optional; without one, Hugging Face may print
a rate-limit warning that does not affect local indexing or benchmark results.

Inspect either retriever directly:

```powershell
uv run apollo query --pipeline baseline "What is the fine for Section 76(4)?"
uv run apollo query --pipeline docling "What is the fine for Section 76(4)?"
```

Generated artifacts are separated from raw data:

- `data/chroma/` - persistent Chroma database
- `data/processed/docling/` - layout-aware Markdown and lossless Docling JSON
- `reports/phase1_benchmark.json` - metrics and ranked evidence
- `reports/phase1_benchmark.md` - comparison table and audit trail

## Quality checks

```powershell
uv run pytest
uv run ruff check .
```

## Design boundaries

- Both pipelines ingest exactly the same source files.
- Collections are rebuilt per pipeline to avoid stale duplicate chunks.
- Both collections use the same embedding function for a fair comparison.
- The benchmark does not call an LLM, so it cannot conceal a retrieval failure.
