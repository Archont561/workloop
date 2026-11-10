#!/usr/bin/env bash
# Start a working session from a clean checkout: restore sandbox if needed,
# install dependencies, install Git hooks, and run fast sanity checks.
set -euo pipefail

SKIP_RESTORE=0
SKIP_HOOKS=0
SKIP_CHECKS=0
NO_FETCH=0

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap.sh [options]

  --skip-restore   do not run the sandbox restore even when the environment is missing
  --skip-hooks     do not install the lefthook Git hooks
  --skip-checks    do not run post-setup smoke checks
  --no-fetch       do not contact the remote; inspect the checkout as-is
  -h, --help       show this message
EOF
}

for argument in "$@"; do
  case "$argument" in
    --skip-restore) SKIP_RESTORE=1 ;;
    --skip-hooks) SKIP_HOOKS=1 ;;
    --skip-checks) SKIP_CHECKS=1 ;;
    --no-fetch) NO_FETCH=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "bootstrap: unknown option $argument" >&2; usage >&2; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }
problem() { printf 'bootstrap: %s\n' "$*" >&2; }

main() {
  local root
  if ! root=$(git rev-parse --show-toplevel 2>/dev/null); then
    problem "run this from inside a Git checkout"
    exit 1
  fi
  say "bootstrap: $root"

  if [ "$NO_FETCH" -eq 0 ] && git -C "$root" remote get-url origin >/dev/null 2>&1; then
    local branch
    branch=$(git -C "$root" symbolic-ref --quiet --short HEAD || true)
    if [ -n "$branch" ]; then
      git -C "$root" ls-remote --exit-code --quiet --heads origin "$branch" >/dev/null 2>&1 && \
        git -C "$root" fetch --quiet origin "+refs/heads/$branch:refs/remotes/origin/$branch" || true
    fi
  fi

  if [ "$SKIP_RESTORE" -eq 0 ]; then
    if ! command -v pixi >/dev/null 2>&1 || [ ! -x "$root/.pixi/envs/default/bin/python" ]; then
      if [ -f "$root/scripts/restore.sh" ]; then
        bash "$root/scripts/restore.sh"
      fi
    fi
  fi

  if [ "$SKIP_HOOKS" -eq 0 ] && [ -d "$root/.git" ]; then
    pixi run --frozen --no-install hooks-install
  fi

  if [ "$SKIP_CHECKS" -eq 0 ]; then
    pixi run --frozen --no-install test-tools
    pixi run --frozen --no-install alint
  fi

  say "bootstrap: ready"
}

main "$@"
