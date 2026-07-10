#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

UV_VERSION=0.11.28
UV_BIN=""

if command -v uv >/dev/null 2>&1 && [ "$(uv --version)" = "uv $UV_VERSION" ]; then
  UV_BIN=$(command -v uv)
else
  if [ ! -x ".tools/uv/bin/uv" ]; then
    python3 -m venv .tools/uv
    .tools/uv/bin/python -m pip install --disable-pip-version-check "uv==$UV_VERSION"
  fi
  UV_BIN=.tools/uv/bin/uv
fi

"$UV_BIN" sync --frozen --all-groups
Rscript --vanilla scripts/bootstrap_renv.R

printf '%s\n' "bootstrap-ok uv=$UV_VERSION"
