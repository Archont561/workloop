#!/usr/bin/env python3
"""Enforce minimum Rust line coverage over `coverage/lcov.info`."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_THRESHOLD = 90.0
SOURCE_PREFIXES = ("crates/workloop-core/src/", "crates/workloop/src/")


@dataclass(frozen=True)
class CoverageSummary:
    """Aggregated line coverage across workspace Rust source files."""

    covered_lines: int
    total_lines: int
    per_file: dict[str, tuple[int, int]]

    @property
    def percent(self) -> float:
        if self.total_lines == 0:
            return 0.0
        return (self.covered_lines / self.total_lines) * 100.0


def normalize_source_path(raw_path: str, root: Path) -> str:
    """Normalize an LCOV `SF:` path relative to `root`."""
    candidate = Path(raw_path)
    resolved_root = root.resolve()
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(resolved_root).as_posix()
        except ValueError:
            return candidate.as_posix()
    return candidate.as_posix()


def parse_lcov(lcov_text: str, root: Path) -> CoverageSummary:
    """Parse LCOV records belonging to `crates/*/src/`."""
    hits_by_file: dict[str, dict[int, int]] = {}
    current_file: str | None = None

    for raw_line in lcov_text.splitlines():
        line = raw_line.strip()
        if line.startswith("SF:"):
            rel = normalize_source_path(line[3:], root)
            if rel.startswith(SOURCE_PREFIXES):
                current_file = rel
                hits_by_file.setdefault(rel, {})
            else:
                current_file = None
        elif line == "end_of_record":
            current_file = None
        elif current_file is not None and line.startswith("DA:"):
            payload = line[3:].split(",")
            if len(payload) >= 2:
                lineno = int(payload[0])
                count = int(payload[1])
                prev = hits_by_file[current_file].get(lineno, 0)
                hits_by_file[current_file][lineno] = max(prev, count)

    per_file: dict[str, tuple[int, int]] = {}
    total_covered = 0
    total_lines = 0
    for rel, line_map in sorted(hits_by_file.items()):
        covered = sum(1 for count in line_map.values() if count > 0)
        count_total = len(line_map)
        per_file[rel] = (covered, count_total)
        total_covered += covered
        total_lines += count_total

    return CoverageSummary(
        covered_lines=total_covered,
        total_lines=total_lines,
        per_file=per_file,
    )


def verify_coverage(
    lcov_path: Path,
    root: Path,
    threshold: float = DEFAULT_THRESHOLD,
) -> tuple[CoverageSummary, list[str]]:
    """Verify `lcov_path` exists, covers both crates, and meets `threshold`."""
    if not lcov_path.is_file():
        return CoverageSummary(0, 0, {}), [f"missing LCOV report: {lcov_path}"]

    summary = parse_lcov(lcov_path.read_text(encoding="utf-8"), root)
    problems: list[str] = []
    if summary.total_lines == 0:
        problems.append("LCOV report contains zero instrumented source lines under crates/*/src/")
        return summary, problems

    problems.extend(
        f"LCOV report has no records under {prefix}"
        for prefix in SOURCE_PREFIXES
        if not any(path.startswith(prefix) for path in summary.per_file)
    )

    if summary.percent < threshold:
        problems.append(
            f"Rust line coverage {summary.percent:.2f}% "
            f"({summary.covered_lines}/{summary.total_lines}) is below {threshold:.2f}%"
        )
    return summary, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--lcov", type=Path, default=Path("coverage/lcov.info"))
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = parser.parse_args(argv)

    lcov_path = args.lcov if args.lcov.is_absolute() else args.root / args.lcov
    summary, problems = verify_coverage(lcov_path, args.root, args.threshold)
    if problems:
        for problem in problems:
            print(f"coverage: {problem}", file=sys.stderr)
        return 1

    print(
        f"coverage: {summary.percent:.2f}% "
        f"({summary.covered_lines}/{summary.total_lines} lines >= {args.threshold:.1f}%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
