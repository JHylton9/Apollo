# Phase 1 methodology

## Research question

How does standard PDF text/OCR chunking compare with Docling's layout-aware parsing when
retrieving exact legal, statistical, and registry evidence from the supplied JCF corpus?

## Controlled variables

- Identical five-file source corpus.
- Identical Chroma embedding function and cosine-distance configuration.
- Identical natural-language queries and top-k value.
- Identical source-hit, reciprocal-rank, and evidence-coverage calculations.
- No LLM generation during scoring.

## Independent variable

The document representation and chunking strategy:

- Baseline: page text or OCR, then 1,000-character recursive chunks with 200-character
  overlap.
- Structural: Docling layout/table conversion and hybrid hierarchical chunks with repeated
  table headers.

## Metrics

`source_hit_rate` is the fraction of questions where the expected source appears in the
top-k. `mean_reciprocal_rank` rewards placing that source early. `evidence_coverage` is the
fraction of question-specific evidence groups present across the retrieved chunks. The last
metric is deliberately stricter than checking only the document name.

## Required qualitative review

The generated report includes ranked evidence previews. Review those previews for:

1. Correct fine-description-amount-points-section alignment.
2. Correct division-year-measure alignment in the wide crime matrix.
3. Correct year-count alignment across the historical table's four pages.
4. Complete wanted-person names, alleged offences, and public reporting numbers.

The comparison must report failures honestly. A structural parser can preserve tables better
while a page OCR pipeline can flatten a wide table and lose column relationships. Phase 1
measures that trade-off.

## Reproduction

```powershell
uv sync --extra dev
uv run apollo ingest --pipeline all
uv run apollo benchmark --top-k 5
```

The Markdown and JSON reports are written under `reports/`. Docling's Markdown and lossless
JSON exports are written under `data/processed/docling/` for direct inspection.
