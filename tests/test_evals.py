"""Keep the lightweight evaluation dataset executable in CI."""

from __future__ import annotations

import json
from pathlib import Path


def test_eval_dataset_has_explicit_oracles() -> None:
    dataset = Path("evals/dataset.jsonl")
    cases = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    assert cases
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert case["question"]
        assert isinstance(case["expected_keywords"], list)
        assert "expected_tool" in case
        assert "expected_source" in case
