from pathlib import Path

from apollo.evaluation.benchmark import load_cases


def test_benchmark_manifest_loads() -> None:
    path = Path(__file__).parents[2] / "benchmarks" / "phase1_queries.json"
    cases = load_cases(path)
    assert len(cases) == 4
    assert all(case.evidence_groups for case in cases)
