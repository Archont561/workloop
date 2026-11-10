"""Append Markdown summaries when running inside GitHub Actions."""

from __future__ import annotations

import os
from pathlib import Path


def append_summary(markdown: str) -> None:
    """Append `markdown` to `$GITHUB_STEP_SUMMARY` when set."""
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return
    path = Path(summary_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(markdown.rstrip() + "\n\n")
