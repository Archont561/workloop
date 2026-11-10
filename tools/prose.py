#!/usr/bin/env python3
"""Render and verify the Vale prose config (`vale.toml` -> `.vale.ini`, `.vale/styles/`)."""

from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.lib.github_actions import append_summary

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "vale.toml"
INI = ROOT / ".vale.ini"
STYLES = ROOT / ".vale" / "styles"
STYLE = "Workloop"
ANNOTATION_LIMIT = 10

CHECKS: dict[str, frozenset[str]] = {
    "existence": frozenset({"tokens", "raw", "ignorecase", "nonword", "scope", "exceptions"}),
    "substitution": frozenset({"swap", "ignorecase", "nonword", "scope", "exceptions"}),
}


def scalar(value: Any) -> str:
    """Format one YAML scalar cleanly."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text and not re.search(r"[^A-Za-z0-9 _./$-]", text) and text.strip() == text:
        return text
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


class ConfigError(Exception):
    """Raised when `vale.toml` violates rendering constraints."""


@dataclass(frozen=True)
class Rule:
    """One rule belonging to the repository's own Vale style."""

    name: str
    extends: str
    message: str
    level: str
    body: dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        lines = [
            f"extends: {self.extends}",
            f"message: {scalar(self.message)}",
            f"level: {self.level}",
        ]
        for key, value in self.body.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                lines.extend(f"  {scalar(k)}: {scalar(v)}" for k, v in value.items())
            else:
                lines.append(f"{key}: {scalar(value)}")
        return "\n".join(lines) + "\n"


def load(path: Path = CONFIG) -> dict[str, Any]:
    """Load and validate `vale.toml`."""
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigError(f"{path} is missing") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path} is not valid TOML: {error}") from error

    for key in ("sources", "packages", "based_on", "vocab"):
        if key not in config:
            raise ConfigError(f"{path} does not set `{key}`")
    if not config["sources"]:
        raise ConfigError(f"{path} names no `sources`")
    if not config["packages"]:
        raise ConfigError(f"{path} pins no `packages`")
    for package in config["packages"]:
        if not package.startswith("https://"):
            raise ConfigError(f"{path} must pin release URL for package `{package}`")

    for name, rule in config.get("rules", {}).items():
        style, _, rule_name = name.partition(".")
        if style in (STYLE, "Vale") or not rule_name:
            continue
        if str(rule.get("level", "")).upper() == "NO" and not str(rule.get("reason", "")).strip():
            raise ConfigError(f"{path} switches `{name}` off without a `reason`")
    return config


def own_rules(config: dict[str, Any]) -> list[Rule]:
    """Extract custom style rules defined under `STYLE`."""
    rules: list[Rule] = []
    for name, spec in config.get("rules", {}).items():
        style, _, rule_name = name.partition(".")
        if style != STYLE or not rule_name:
            continue
        extends = spec.get("extends")
        if extends not in CHECKS:
            raise ConfigError(f"{name} extends `{extends}`; allowed: {', '.join(sorted(CHECKS))}")
        unknown = set(spec) - {"extends", "message", "level", "reason"} - CHECKS[extends]
        if unknown:
            raise ConfigError(
                f"{name} sets unsupported keys for {extends}: {', '.join(sorted(unknown))}"
            )
        if not spec.get("message"):
            raise ConfigError(f"{name} has no `message`")
        body = {key: value for key, value in spec.items() if key in CHECKS[extends]}
        rules.append(Rule(rule_name, extends, spec["message"], spec.get("level", "warning"), body))
    return rules


def render_style(config: dict[str, Any], styles_dir: Path = STYLES) -> dict[Path, str]:
    """Render the repository style YAML rules and accepted vocabulary."""
    files = {styles_dir / STYLE / f"{rule.name}.yml": rule.render() for rule in own_rules(config)}
    accept = config.get("accept", [])
    if not accept:
        raise ConfigError("no `accept` vocabulary entries configured")
    files[styles_dir / "config" / "vocabularies" / config["vocab"] / "accept.txt"] = (
        "\n".join(accept) + "\n"
    )
    return files


def render_ini(config: dict[str, Any]) -> str:
    """Render `.vale.ini` deterministically from `vale.toml`."""
    lines = [
        "# Generated by tools/prose.py from vale.toml. Edit vale.toml, not this file.",
        "",
        "StylesPath = .vale/styles",
        f"MinAlertLevel = {config['min_alert_level']}",
        "",
        "Packages = " + ", ".join(config["packages"]),
        "",
        f"Vocab = {config['vocab']}",
        "",
        "[*.md]",
        "BasedOnStyles = " + ", ".join(config["based_on"]),
    ]
    overrides = {
        name: spec
        for name, spec in config.get("rules", {}).items()
        if not name.startswith(f"{STYLE}.")
    }
    if overrides:
        lines.append("")
        for name, spec in overrides.items():
            level = spec.get("level")
            if level:
                lines.append(f"{name} = {level}")
                reason = " ".join(str(spec.get("reason", "")).split())
                if reason:
                    lines.append(f"#   {reason}")

    lines += [
        "",
        "[backlog/**/*.md]",
        "BasedOnStyles = Vale",
        "",
        "[CHANGELOG.md]",
        "BasedOnStyles = Vale",
        "",
    ]
    return "\n".join(lines)


def rendered(config: dict[str, Any] | None = None, root: Path = ROOT) -> dict[Path, str]:
    """Return every generated file path mapped to its expected content."""
    loaded = load(root / "vale.toml") if config is None else config
    ini_path = root / ".vale.ini"
    styles_dir = root / ".vale" / "styles"
    files = {ini_path: render_ini(loaded)}
    files.update(render_style(loaded, styles_dir=styles_dir))
    return files


def differences(config: dict[str, Any] | None = None, root: Path = ROOT) -> list[str]:
    """Return drift messages between committed files and rendered output."""
    problems: list[str] = []
    for path, content in rendered(config, root=root).items():
        relative = path.relative_to(root)
        try:
            present = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            problems.append(f"{relative}: missing; run `pixi run automation prose_write`")
            continue
        if present != content:
            problems.append(f"{relative}: out of date; run `pixi run automation prose_write`")
    return problems


def write(config: dict[str, Any] | None = None, root: Path = ROOT) -> list[Path]:
    """Write all rendered files under `root`."""
    written: list[Path] = []
    for path, content in rendered(config, root=root).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def sources(config: dict[str, Any] | None = None, root: Path = ROOT) -> list[str]:
    """Expand configured prose sources into relative Markdown paths."""
    loaded = load(root / "vale.toml") if config is None else config
    files: list[str] = []
    for entry in loaded["sources"]:
        path = root / entry
        if path.is_dir():
            files.extend(sorted(str(p.relative_to(root)) for p in path.rglob("*.md")))
        elif path.is_file():
            files.append(entry)
        else:
            raise ConfigError(f"`sources` names missing path `{entry}`")
    return files


def vale_command(config: dict[str, Any] | None = None, root: Path = ROOT) -> list[str]:
    """Build the Vale CLI invocation."""
    loaded = load(root / "vale.toml") if config is None else config
    return ["vale", "--config", ".vale.ini", *sources(loaded, root=root)]


def lint(config: dict[str, Any] | None = None, root: Path = ROOT) -> int:
    """Run Vale over configured Markdown files."""
    loaded = load(root / "vale.toml") if config is None else config
    cmd = vale_command(loaded, root=root)
    command = [cmd[0], "--output=JSON", *cmd[1:]]
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        message = "prose: `vale` is not installed; install Pixi environment and rerun"
        print(message, file=sys.stderr)
        append_summary(f"## Prose: not run\n\n{message}")
        return 1

    try:
        report = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        print(result.stderr or result.stdout, file=sys.stderr)
        return result.returncode or 1

    counts: collections.Counter[str] = collections.Counter()
    findings: list[tuple[str, int, int, str]] = []
    for path, alerts in report.items():
        for alert in alerts:
            counts[alert["Check"]] += 1
            findings.append(
                (
                    path,
                    alert.get("Line", 1),
                    alert.get("Span", [1, 1])[0],
                    f"{alert['Check']}: {alert['Message']}",
                )
            )

    if counts:
        lines = [f"| {count} | `{rule}` |" for rule, count in counts.most_common()]
        append_summary(
            "\n".join(["## Prose: Vale", "", "| Alerts | Rule |", "| ---: | --- |", *lines])
        )
        for path, line, column, msg in findings[:ANNOTATION_LIMIT]:
            escaped = msg.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(
                f"::error file={path},line={line},col={column},title=Prose::{escaped}",
                file=sys.stderr,
            )

    if result.returncode == 0:
        print(f"prose: {len(sources(loaded, root=root))} page(s) pass")
    return result.returncode


def sync(root: Path = ROOT) -> int:
    """Write generated Vale config and fetch pinned upstream Vale packages."""
    config = load(root / "vale.toml")
    write(config, root=root)
    styles_dir = root / ".vale" / "styles"
    styles_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["vale", "sync", "--config=.vale.ini"], cwd=root, check=False)
    if result.returncode != 0:
        print("prose: `vale sync` failed", file=sys.stderr)
        return result.returncode
    print("prose: synced upstream Vale packages")
    return 0


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description="Render and verify Vale configuration.")
    parser.add_argument(
        "action",
        choices=("check", "write", "sync", "lint", "list", "command"),
        nargs="?",
        default="check",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    arguments = parser.parse_args(argv)

    try:
        config = load(root / "vale.toml")
        if arguments.action == "write":
            for path in write(config, root=root):
                print(f"prose: wrote {path.relative_to(root)}")
            return 0
        if arguments.action == "sync":
            return sync(root=root)
        if arguments.action == "lint":
            return lint(config, root=root)
        if arguments.action == "list":
            pages = sources(config, root=root)
            print(json.dumps(pages) if arguments.format == "json" else "\n".join(pages))
            return 0
        if arguments.action == "command":
            print(" ".join(vale_command(config, root=root)))
            return 0
        problems = differences(config, root=root)
    except ConfigError as error:
        print(f"prose: {error}", file=sys.stderr)
        return 1

    if problems:
        for problem in problems:
            print(f"prose: {problem}", file=sys.stderr)
        return 1
    print(f"prose: {len(sources(config, root=root))} page(s), current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
