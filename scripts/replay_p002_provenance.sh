#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^[0-9a-f]{40}$ ]]; then
  echo "usage: $0 <40-character-git-commit>" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMIT="$1"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/delta-p002-replay.XXXXXX")"
CLONE="$SCRATCH/repository"
trap 'rm -rf "$SCRATCH"' EXIT

git -C "$ROOT" cat-file -e "${COMMIT}^{commit}"
git clone --no-local --quiet "$ROOT" "$CLONE"
git -C "$CLONE" checkout --detach --quiet "$COMMIT"

(
  cd "$CLONE"
  ./scripts/bootstrap.sh
  ./scripts/verify.sh
  shasum -a 256 -c provenance/evidence/P002/claude-independent-review.sha256
  test -z "$(git status --porcelain=v1)"
)

printf 'replay-ok commit=%s\n' "$COMMIT"
