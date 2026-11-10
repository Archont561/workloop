#!/usr/bin/env python3
"""Claim exactly one backlog task card for a loop, without two loops colliding.

`hooks.next_task` in `workloop.toml` selects the next card by querying the
backlog. A query is not a reservation: two loops started together read the same
`To Do` list and both pick the first card. This command closes that window.

It takes an exclusive lock over the claim transaction, re-reads the backlog
inside the lock, moves the first unclaimed card to `In Progress`, rewrites the
frontmatter, and prints the card id on stdout. Anything that goes wrong ends in a
non-zero exit and an untouched card, so a caller can treat the exit code as the
answer:

    0   a card was claimed, its id is the only line on stdout
    1   no unclaimed card is available (nothing was written)
    2   usage or environment error (nothing was written)

The claim is deliberately a filesystem transaction over `backlog/` rather than a
server-side reservation, because `workloop` must not depend on any particular
backlog implementation. Concurrency across machines is out of scope; the lock
covers one repository checkout, which is one loop's working directory.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import re
import sys
from collections.abc import Iterator
from pathlib import Path

UNCLAIMED_STATUS = "To Do"
CLAIMED_STATUS = "In Progress"
LOCK_NAME = ".claim.lock"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
ID_RE = re.compile(r"^id:\s*(.+?)\s*$", re.MULTILINE)
STATUS_RE = re.compile(r"^status:\s*(.+?)\s*$", re.MULTILINE)


class ClaimError(Exception):
    """Raised when the claim cannot proceed for a reason other than an empty queue."""


def _field(frontmatter: str, regex: re.Pattern[str]) -> str:
    """Return the first captured value of `regex`, stripped of quotes."""
    match = regex.search(frontmatter)
    return match.group(1).strip().strip("'\"") if match else ""


def unclaimed_cards(backlog_dir: Path) -> list[Path]:
    """Return every task card still in the unclaimed status, in filename order."""
    tasks = backlog_dir / "tasks"
    if not tasks.is_dir():
        msg = f"missing tasks directory: {tasks}"
        raise ClaimError(msg)
    claimed: list[Path] = []
    for card in sorted(tasks.glob("*.md")):
        frontmatter = FRONTMATTER_RE.match(card.read_text(encoding="utf-8"))
        if frontmatter is None:
            continue
        if _field(frontmatter.group(1), STATUS_RE) == UNCLAIMED_STATUS:
            claimed.append(card)
    return claimed


def claim(card: Path) -> str:
    """Move one card to the claimed status and return its id.

    The rewrite touches only the `status:` line, so frontmatter order, comments,
    and the rest of the file stay byte-identical.
    """
    text = card.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if match is None:
        msg = f"{card.name}: no frontmatter to claim"
        raise ClaimError(msg)
    frontmatter = match.group(1)
    card_id = _field(frontmatter, ID_RE)
    if not card_id:
        msg = f"{card.name}: no id in frontmatter"
        raise ClaimError(msg)
    updated_frontmatter = STATUS_RE.sub(f"status: {CLAIMED_STATUS}", frontmatter, count=1)
    card.write_text(
        f"---\n{updated_frontmatter}\n---\n" + text[match.end() :],
        encoding="utf-8",
    )
    return card_id


@contextlib.contextmanager
def claim_lock(backlog_dir: Path) -> Iterator[None]:
    """Hold an exclusive lock for the read-claim-write transaction.

    An advisory `flock` is enough here because every claimer in a checkout runs
    this same command. The lock file is gitignored with the rest of the runtime
    state, and the directory is created when absent so `init` is not a
    prerequisite for the first claim.
    """
    backlog_dir.mkdir(parents=True, exist_ok=True)
    with (backlog_dir / LOCK_NAME).open("w", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def claim_next(backlog_dir: Path) -> str | None:
    """Claim the first available card, or return `None` when the queue is empty."""
    with claim_lock(backlog_dir):
        available = unclaimed_cards(backlog_dir)
        if not available:
            return None
        return claim(available[0])


def main(argv: list[str] | None = None) -> int:
    """Run the claim transaction and translate its outcome into an exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backlog-dir",
        type=Path,
        default=Path("backlog"),
        help="Backlog directory to claim from (default: ./backlog)",
    )
    arguments = parser.parse_args(argv)
    try:
        card_id = claim_next(arguments.backlog_dir)
    except ClaimError as error:
        print(f"claim: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"claim: {error}", file=sys.stderr)
        return 2
    if card_id is None:
        print("claim: no unclaimed task available", file=sys.stderr)
        return 1
    print(card_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
