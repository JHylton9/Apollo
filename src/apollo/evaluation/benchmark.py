from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apollo.models import BenchmarkCase, PipelineName
from apollo.retrieval.store import VectorStore
from apollo.text import normalized


def load_cases(path: Path) -> list[BenchmarkCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        BenchmarkCase(
            id=item["id"],
            question=item["question"],
            expected_source=item["expected_source"],
            evidence_groups=tuple(tuple(group) for group in item["evidence_groups"]),
        )
        for item in payload["cases"]
    ]


def evaluate(
    store: VectorStore,
    cases: list[BenchmarkCase],
    pipelines: tuple[PipelineName, ...] = ("baseline", "docling"),
    top_k: int = 5,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "top_k": top_k,
        "pipelines": {},
    }
    for pipeline in pipelines:
        rows = []
        for case in cases:
            hits = store.query(pipeline, case.question, top_k=top_k)
            evidence_text = normalized("\n".join(hit.text for hit in hits))
            # Each group contains equivalent text forms produced by either parser.
            group_scores = [
                float(any(normalized(term) in evidence_text for term in group))
                for group in case.evidence_groups
            ]
            # Reciprocal rank rewards placing the expected document near the top.
            source_ranks = [
                rank
                for rank, hit in enumerate(hits, start=1)
                if hit.source.casefold() == case.expected_source.casefold()
            ]
            reciprocal_rank = 1.0 / source_ranks[0] if source_ranks else 0.0
            rows.append(
                {
                    "id": case.id,
                    "question": case.question,
                    "expected_source": case.expected_source,
                    "source_hit": bool(source_ranks),
                    "reciprocal_rank": reciprocal_rank,
                    "evidence_coverage": sum(group_scores) / max(len(group_scores), 1),
                    "matched_groups": int(sum(group_scores)),
                    "total_groups": len(group_scores),
                    "hits": [
                        {
                            "rank": rank,
                            "source": hit.source,
                            "page": hit.page,
                            "score": round(hit.score, 4),
                            "preview": hit.text[:500],
                        }
                        for rank, hit in enumerate(hits, start=1)
                    ],
                }
            )
        report["pipelines"][pipeline] = {
            "chunk_count": store.count(pipeline),
            "source_hit_rate": sum(row["source_hit"] for row in rows) / max(len(rows), 1),
            "mean_reciprocal_rank": sum(row["reciprocal_rank"] for row in rows) / max(len(rows), 1),
            "mean_evidence_coverage": sum(row["evidence_coverage"] for row in rows)
            / max(len(rows), 1),
            "cases": rows,
        }
    return report


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 1 Retrieval Benchmark",
        "",
        f"Generated: `{report['generated_at']}`  ",
        f"Top-k: `{report['top_k']}`",
        "",
        "## Summary",
        "",
        "| Pipeline | Chunks | Source hit rate | MRR | Evidence coverage |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, data in report["pipelines"].items():
        lines.append(
            f"| {name} | {data['chunk_count']} | {data['source_hit_rate']:.1%} | "
            f"{data['mean_reciprocal_rank']:.3f} | {data['mean_evidence_coverage']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Comparative interpretation",
            "",
            "The metrics evaluate retrieval only; they do not claim that a generated answer is "
            "factually correct. Source hit rate measures whether the expected PDF appears in the "
            "top-k, MRR rewards higher ranking, and evidence coverage checks whether the retrieved "
            "set contains the expected answer-bearing facts.",
            "",
            "| Case | Baseline coverage | Docling coverage | Difference |",
            "|---|---:|---:|---:|",
        ]
    )
    baseline_cases = {item["id"]: item for item in report["pipelines"]["baseline"]["cases"]}
    docling_cases = {item["id"]: item for item in report["pipelines"]["docling"]["cases"]}
    for case_id, baseline in baseline_cases.items():
        docling = docling_cases[case_id]
        difference = docling["evidence_coverage"] - baseline["evidence_coverage"]
        lines.append(
            f"| {case_id} | {baseline['evidence_coverage']:.1%} | "
            f"{docling['evidence_coverage']:.1%} | {difference:+.1%} |"
        )
    lines.extend(
        [
            "",
            "Qualitative review should accompany these values. In particular, inspect whether "
            "fine amounts remain attached to their descriptions and legal sections, whether each "
            "division retains the correct year/value columns, and whether OCR captures text inside "
            "the wanted/missing-person cards. A lower score is a documented finding, not a result "
            "to conceal; use the ranked evidence below to explain the failure mode.",
        ]
    )
    for name, data in report["pipelines"].items():
        lines.extend(["", f"## {name.title()} results", ""])
        for case in data["cases"]:
            lines.extend(
                [
                    f"### {case['id']}",
                    "",
                    case["question"],
                    "",
                    f"- Source found: **{case['source_hit']}**",
                    f"- Reciprocal rank: **{case['reciprocal_rank']:.3f}**",
                    f"- Evidence coverage: **{case['evidence_coverage']:.1%}** "
                    f"({case['matched_groups']}/{case['total_groups']})",
                    "- Retrieved evidence:",
                ]
            )
            for hit in case["hits"]:
                page = f", p. {hit['page']}" if hit["page"] else ""
                preview = " ".join(hit["preview"].split())
                lines.append(
                    f"  {hit['rank']}. `{hit['source']}{page}` score={hit['score']:.4f} - {preview}"
                )
    lines.append("")
    return "\n".join(lines)
