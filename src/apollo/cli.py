from __future__ import annotations

import json
import sys
from typing import Annotated, Literal

import typer
from rich.console import Console
from rich.table import Table

from apollo.evaluation.benchmark import evaluate, load_cases, markdown_report
from apollo.ingestion import BaselinePipeline, DoclingPipeline
from apollo.models import PipelineName, Settings
from apollo.retrieval.store import VectorStore
from apollo.text import pdf_files

app = typer.Typer(
    no_args_is_help=True,
    help="Apollo JCF assistant: ingestion, benchmark and agent chat",
)
console = Console()


def _terminal_safe(value: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return value.encode(encoding, errors="replace").decode(encoding)


def _settings() -> Settings:
    settings = Settings.from_root()
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    return settings


@app.command()
def ingest(
    pipeline: Annotated[
        Literal["baseline", "docling", "all"],
        typer.Option(help="Pipeline to build."),
    ] = "all",
) -> None:
    """Parse the JCF PDFs and rebuild persistent Chroma collections."""
    settings = _settings()
    files = pdf_files(settings.raw_dir)
    if not files:
        raise typer.BadParameter(f"No PDFs found in {settings.raw_dir}")
    store = VectorStore(settings.chroma_dir)
    selected = ("baseline", "docling") if pipeline == "all" else (pipeline,)
    for name in selected:
        # Build each collection from the complete, identical PDF set.
        chunks = []
        if name == "baseline":
            worker = BaselinePipeline(settings.chunk_size, settings.chunk_overlap)
            for path in files:
                console.print(f"[cyan]Baseline[/] {path.name}")
                chunks.extend(worker.ingest(path))
        else:
            worker = DoclingPipeline()
            output_dir = settings.processed_dir / "docling"
            output_dir.mkdir(parents=True, exist_ok=True)
            for path in files:
                console.print(f"[magenta]Docling[/] {path.name}")
                document_chunks, artifact = worker.ingest(path)
                chunks.extend(document_chunks)
                stem = path.stem.replace(" ", "_")
                (output_dir / f"{stem}.md").write_text(artifact["markdown"], encoding="utf-8")
                (output_dir / f"{stem}.json").write_text(
                    json.dumps(artifact["document"], ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        count = store.rebuild(name, chunks)  # type: ignore[arg-type]
        console.print(f"[green]Indexed {count} {name} chunks.[/]")


@app.command()
def query(
    question: Annotated[str, typer.Argument(help="Retrieval query")],
    pipeline: Annotated[PipelineName, typer.Option()] = "docling",
    top_k: Annotated[int, typer.Option(min=1, max=20)] = 5,
) -> None:
    """Inspect retrieved chunks and their citation metadata."""
    settings = _settings()
    hits = VectorStore(settings.chroma_dir).query(pipeline, question, top_k)
    for index, hit in enumerate(hits, start=1):
        page = f" page {hit.page}" if hit.page else ""
        console.rule(f"{index}. {hit.source}{page} - {hit.score:.4f}")
        console.print(_terminal_safe(hit.text))


@app.command()
def benchmark(top_k: Annotated[int, typer.Option(min=1, max=20)] = 5) -> None:
    """Compare retrieval quality and save JSON plus Markdown evidence reports."""
    settings = _settings()
    store = VectorStore(settings.chroma_dir)
    for pipeline in ("baseline", "docling"):
        if store.count(pipeline) == 0:
            raise typer.BadParameter(f"{pipeline} collection is empty; run `apollo ingest` first")
    report = evaluate(store, load_cases(settings.benchmark_file), top_k=top_k)
    # Save a detailed audit trail alongside the console summary.
    json_path = settings.reports_dir / "phase1" / "benchmark.json"
    md_path = settings.reports_dir / "phase1" / "benchmark.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")

    table = Table(title="Phase 1 retrieval benchmark")
    for column in ("Pipeline", "Chunks", "Source hit", "MRR", "Evidence"):
        table.add_column(column)
    for name, data in report["pipelines"].items():
        table.add_row(
            name,
            str(data["chunk_count"]),
            f"{data['source_hit_rate']:.1%}",
            f"{data['mean_reciprocal_rank']:.3f}",
            f"{data['mean_evidence_coverage']:.1%}",
        )
    console.print(table)
    console.print(f"Reports: {md_path}")


@app.command()
def chat() -> None:
    """Chat with Apollo coordinator; high risk asctions pause for review"""
    from apollo.agents.terminal import run_chat

    run_chat(console)


@app.command()
def status() -> None:
    """Show corpus and collection readiness."""
    settings = _settings()
    store = VectorStore(settings.chroma_dir)
    table = Table(title="Apollo Phase 1 status")
    table.add_column("Item")
    table.add_column("Count", justify="right")
    table.add_row("Source PDFs", str(len(pdf_files(settings.raw_dir))))
    table.add_row("Baseline chunks", str(store.count("baseline")))
    table.add_row("Docling chunks", str(store.count("docling")))
    console.print(table)


if __name__ == "__main__":
    app()
