#!/usr/bin/env python3
"""Render and verify CHANGELOG.md from Conventional Commits via convco."""

from __future__ import annotations

import argparse
import datetime
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = "CHANGELOG.md"
_OWNER = "Archont561"
_REPOSITORY = "workloop"

Output = Callable[[Sequence[str]], tuple[int, str]]

VERSION_HEADING = re.compile(
    r"""^\#+\s+
        (?:
            \[(?P<bracket>[^\]]+)\](?:\((?P<url>[^)]*)\))?
          | (?P<plain>v?\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?)
          | (?P<word>Unreleased)
        )
        (?:\s+"[^"]*")?
        (?:\s+-\s+(?P<dash_date>\d{4}-\d{2}-\d{2}))?
        (?:\s+\((?P<paren_date>\d{4}-\d{2}-\d{2})\))?
        \s*$""",
    re.VERBOSE,
)
HEADING = re.compile(r"^#+\s+")
UNRELEASED = "Unreleased"


class ChangelogError(RuntimeError):
    """Raised when the changelog cannot be rendered or checked."""


def _version_heading(line: str) -> tuple[str, str | None, str | None] | None:
    match = VERSION_HEADING.match(line)
    if match is None:
        return None
    name = match.group("bracket") or match.group("plain") or match.group("word") or ""
    name = re.sub(r"^v", "", name.strip())
    date = match.group("dash_date") or match.group("paren_date")
    return name, match.group("url"), date


def render(raw: str, *, include_links: bool = True) -> str:
    """Normalize convco changelog output into Keep a Changelog format."""
    lines: list[str] = []
    links: list[tuple[str, str]] = []
    seen_version = False

    for line in raw.splitlines():
        heading = _version_heading(line)
        if heading is not None:
            name, url, date = heading
            seen_version = True
            if name == UNRELEASED:
                lines.append(f"## [{UNRELEASED}]")
                if url:
                    links.append((name, re.sub(r"\.\.\.[^/]+$", "...HEAD", url)))
                continue
            lines.append(f"## [{name}] - {date}" if date else f"## [{name}]")
            if url:
                links.append((name, url))
            continue
        if seen_version and HEADING.match(line):
            lines.append(f"### {HEADING.sub('', line).strip()}")
            continue
        lines.append(line.rstrip())

    text: list[str] = []
    for line in lines:
        if not line.strip():
            if text and text[-1] != "":
                text.append("")
            continue
        if line.startswith("#") and text and text[-1] != "":
            text.append("")
        text.append(line)
    while text and text[-1] == "":
        text.pop()

    if include_links and links:
        text.append("")
        text.extend(f"[{name}]: {url}" for name, url in links)
    return "\n".join(text) + "\n"


def with_unreleased(raw: str) -> str:
    """Ensure an `Unreleased` section is present even when HEAD sits at a release tag."""
    lines = raw.splitlines()
    for index, line in enumerate(lines):
        heading = _version_heading(line)
        if heading is None:
            continue
        name, url, _ = heading
        if name == UNRELEASED:
            return raw
        if url and "/compare/" in url and "..." in url:
            base, tag = url.split("/compare/", 1)[0], url.rsplit("...", 1)[1]
        else:
            base, tag = f"https://github.com/{_OWNER}/{_REPOSITORY}", f"v{name}"
        lines[index:index] = [f"## [{UNRELEASED}]({base}/compare/{tag}...HEAD)", ""]
        return "\n".join(lines) + "\n"
    return raw


def convco(root: Path) -> Output:
    """Return a runner bound to `convco` inside `root`."""

    def run(argv: Sequence[str]) -> tuple[int, str]:
        executable = shutil.which("convco")
        if executable is None:
            raise ChangelogError("convco is not on PATH; run through Pixi")
        result = subprocess.run(
            [executable, *argv],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout + result.stderr

    return run


def generate(runner: Output, root: Path) -> str:
    """Render CHANGELOG.md text from git history."""
    del root
    code, output = runner(["changelog"])
    if code != 0:
        raise ChangelogError(f"convco changelog failed (exit {code}):\n{output.strip()}")
    return render(with_unreleased(output))


def notes_for(runner: Output, version: str, date: str | None = None) -> str:
    """Render release notes for `version` since the last tag."""
    code, output = runner(["changelog", "--unreleased", version])
    if code != 0:
        raise ChangelogError(f"convco changelog failed (exit {code}):\n{output.strip()}")
    release_date = date or datetime.datetime.now(datetime.UTC).date().isoformat()
    body = [line for line in output.splitlines() if _version_heading(line) is None]
    return render("\n".join([f"## [{version}] - {release_date}", *body]), include_links=False)


def main(
    argv: Sequence[str] | None = None,
    root: Path = ROOT,
    runner: Output | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="Render and verify CHANGELOG.md.")
    parser.add_argument(
        "action",
        nargs="?",
        default="regen",
        choices=["regen", "check", "print", "notes"],
    )
    parser.add_argument("version", nargs="?", help="version for `notes`")
    parser.add_argument("--date", help="ISO release date for `notes`")
    arguments = parser.parse_args(argv)

    execute = runner or convco(root)
    changelog = root / CHANGELOG

    try:
        if arguments.action == "notes":
            if not arguments.version:
                parser.error("notes requires a version argument")
            sys.stdout.write(notes_for(execute, arguments.version, arguments.date))
            return 0

        rendered = generate(execute, root)
        if arguments.action == "print":
            sys.stdout.write(rendered)
            return 0
        if arguments.action == "check":
            current = changelog.read_text(encoding="utf-8") if changelog.is_file() else ""
            if current != rendered:
                print(
                    f"changelog: {CHANGELOG} does not match rendered history. "
                    "Run `pixi run automation changelog` and commit the result.",
                    file=sys.stderr,
                )
                return 1
            print(f"changelog: {CHANGELOG} matches rendered history")
            return 0
        changelog.write_text(rendered, encoding="utf-8")
        print(f"changelog: wrote {CHANGELOG}")
        return 0
    except ChangelogError as error:
        print(f"changelog: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
