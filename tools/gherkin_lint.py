#!/usr/bin/env python3
"""Lint every `features/*.feature` file across crates and tools."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from gherlint.linter import GherkinLinter
from gherlint.objectmodel.nodes import Document, Node
from gherlint.reporting import Message, MessageStore, Reporter

FEATURE_DIRECTORY = "features"
FEATURE_SUFFIX = ".feature"

SKIPPED_DIRECTORIES = frozenset(
    {
        ".cargo",
        ".git",
        ".pixi",
        ".pixi-sandbox",
        ".venv",
        "node_modules",
        "output",
        "target",
    }
)


@dataclass(frozen=True)
class Finding:
    """One gherlint diagnostic message."""

    file: str
    line: int
    column: int
    text: str
    name: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}: {self.text} ({self.name})"


class CollectingReporter(Reporter):  # type: ignore[misc]
    """Collect findings instead of printing inline."""

    def __init__(self) -> None:
        super().__init__()
        self.findings: list[Finding] = []

    def emit(self, message: Message, node: Node, **format_args: object) -> None:
        root = node.get_root()
        if not isinstance(root, Document):
            raise RuntimeError("gherlint message emitted outside document")
        text = message.text.format(**format_args) if format_args else message.text
        self.findings.append(
            Finding(
                file=str(root.filename),
                line=node.line,
                column=node.column,
                text=text,
                name=message.name,
            )
        )


def discover(root: Path) -> list[Path]:
    """Return every `features/*.feature` file under `root`."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in SKIPPED_DIRECTORIES)
        if Path(dirpath).name != FEATURE_DIRECTORY:
            continue
        found.extend(
            Path(dirpath) / filename
            for filename in sorted(filenames)
            if filename.endswith(FEATURE_SUFFIX)
        )
    return sorted(found, key=lambda path: path.relative_to(root).as_posix())


def lint_file(path: Path) -> list[Finding]:
    """Run gherlint against a single feature file."""
    reporter = CollectingReporter()
    MessageStore.clear()
    linter = GherkinLinter(path)
    linter.reporter = reporter
    for checker in linter.checkers:
        checker.reporter = reporter
    linter.lint_file(path)
    unique: dict[tuple[str, str], Finding] = {}
    for finding in reporter.findings:
        unique.setdefault((finding.name, finding.text), finding)
    return list(unique.values())


def lint(root: Path) -> tuple[list[Path], list[Finding]]:
    """Discover and lint every feature file under `root`."""
    files = discover(root)
    findings: list[Finding] = []
    for file in files:
        findings.extend(lint_file(file))
    return files, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    files, findings = lint(args.root)
    if not files:
        print(
            f"gherkin-lint: no *{FEATURE_SUFFIX} file under any {FEATURE_DIRECTORY}/ directory",
            file=sys.stderr,
        )
        return 1
    for finding in findings:
        print(f"gherkin-lint: {finding}", file=sys.stderr)
    if findings:
        print(
            f"gherkin-lint: {len(findings)} finding(s) in {len(files)} feature file(s)",
            file=sys.stderr,
        )
        return 1
    print(f"gherkin-lint: {len(files)} feature file(s) clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
