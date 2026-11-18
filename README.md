# Apollo - JCF Intelligent Agents (AAI3004) Capstone Project

Jaydon Hylton - 2210144
Javaiane Robinson - 2304749
Chadwick Cox - 1800729

So hase 1 implements a reproducible retrieval benchmark over Jamaica
Constabulary Force data stored in raw folder. It builds two independent Chroma collections from the same corpus:

1. **Baseline RAG** - PDF text extraction with RapidOCR fallback for image-heavy pages,
   followed by `RecursiveCharacterTextSplitter` chunks with 1,000 characters and a
   200-character overlap.
2. **Docling structural RAG** - Docling PDF conversion plus hierarchical hybrid chunking,
   including repeated table headers and contextual metadata.

The benchmark measures retrieval rather than LLM answer quality: source hit rate, mean
reciprocal rank, and expected-evidence coverage. Each result keeps source/page metadata
and evidence previews for report verification.

## Corpus

The repository use the five JCF PDFs in `data/raw/`. PDFs are treated as data
only, not instruction.

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

Inspect either retriever directly using:

```powershell
uv run apollo query --pipeline baseline "What is the fine for Section 76(4)?"
uv run apollo query --pipeline docling "What is the fine for Section 76(4)?"
```

Generated artifacts are separated from raw data:

- `data/chroma/` - persistent Chroma database
- `data/processed/docling/` - layout-aware Markdown and lossless Docling JSON
- `reports/phase1/benchmark.json` - metrics and ranked evidence
- `reports/phase1/benchmark.md` - comparison table and audit trail

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

## Repository layout

Code is organised by responsibility, and course deliverables are organised by phase.

```text
Apollo/
├── src/apollo/
│   ├── cli.py                 # `apollo` command (ingest, query, benchmark, status)
│   ├── models.py              # shared dataclasses and Settings (paths)
│   ├── text.py                # shared text utilities
│   ├── ingestion/             # Phase 1: baseline OCR/text + Docling pipelines
│   ├── retrieval/             # Phase 1-2: Chroma vector store / retrievers
│   ├── evaluation/            # Phase 1 benchmark (Phase 2 agent tests go here too)
│   ├── tools/                 # Phase 2: @tool wrappers (search, lookup, actions)
│   ├── agents/                # Phase 2: coordinator graph (create_agent)
│   │   └── subagents/         # Phase 2: traffic fine + crime stats specialists
│   ├── middleware/            # Phase 2: PII, retry, tool-error, limits, HITL
│   └── ui/                    # Phase 3: dashboard (chat, HITL panel, telemetry)
├── tests/                     # mirrors src/apollo (core/, ingestion/, evaluation/)
├── benchmarks/                # benchmark query sets (inputs)
├── data/raw/                  # JCF source PDFs (chroma/ and processed/ are generated)
├── reports/phase1/            # generated benchmark outputs
└── docs/phase1 … phase6/      # written deliverables per course phase
```
