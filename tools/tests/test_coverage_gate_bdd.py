"""BDD step definitions for tools/features/coverage_gate.feature."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from tools import coverage_gate

scenarios("../features/coverage_gate.feature")


@dataclass
class CovState:
    root: Path | None = None
    lcov: Path | None = None
    exit_code: int = -1


@pytest.fixture
def state() -> CovState:
    return CovState()


def _write_lcov(root: Path, covered: int, total: int) -> Path:
    half_total = total // 2
    first_cov = min(covered, half_total)
    second_cov = covered - first_cov
    lines = ["TN:", f"SF:{root / 'crates/workloop-core/src/lib.rs'}"]
    for idx in range(1, half_total + 1):
        hits = 1 if idx <= first_cov else 0
        lines.append(f"DA:{idx},{hits}")
    lines.append("end_of_record")
    lines.append(f"SF:{root / 'crates/workloop/src/lib.rs'}")
    for idx in range(1, (total - half_total) + 1):
        hits = 1 if idx <= second_cov else 0
        lines.append(f"DA:{idx},{hits}")
    lines.append("end_of_record")
    lcov_path = root / "coverage" / "lcov.info"
    lcov_path.parent.mkdir(parents=True, exist_ok=True)
    lcov_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lcov_path


@given(
    parsers.parse(
        "a temporary LCOV report with {covered:d} of {total:d} source lines "
        "covered across both crates"
    )
)
def given_lcov(state: CovState, tmp_path: Path, covered: int, total: int) -> None:
    state.root = tmp_path
    state.lcov = _write_lcov(tmp_path, covered, total)


@when(parsers.parse("the coverage gate runs with threshold {threshold:f}"))
def when_run_gate(state: CovState, threshold: float) -> None:
    assert state.root is not None
    assert state.lcov is not None
    state.exit_code = coverage_gate.main(
        ["--root", str(state.root), "--lcov", str(state.lcov), "--threshold", str(threshold)]
    )


@then(parsers.parse("the coverage gate exits with code {code:d}"))
def then_gate_exit(state: CovState, code: int) -> None:
    assert state.exit_code == code
