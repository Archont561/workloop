#!/usr/bin/env sh
# Install lefthook Git hooks from lefthook.yml when running inside a Git checkout.
set -eu

if [ ! -d ".git" ] && ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "install-hooks: not inside a Git repository; skipping" >&2
  exit 0
fi

lefthook install
