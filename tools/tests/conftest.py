"""Shared pytest fixtures for tools/ BDD and unit test suites."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def repo_root() -> Path:
    """Return the live repository root."""
    return REPO_ROOT
