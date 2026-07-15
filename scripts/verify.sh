#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

if [ -x ".tools/uv/bin/uv" ]; then
  UV_BIN=.tools/uv/bin/uv
elif command -v uv >/dev/null 2>&1; then
  UV_BIN=$(command -v uv)
else
  printf '%s\n' "uv not found; run ./scripts/bootstrap.sh first" >&2
  exit 1
fi

"$UV_BIN" run ruff format --check .
"$UV_BIN" run ruff check .
"$UV_BIN" run mypy
"$UV_BIN" run python scripts/generate_p007_schemas.py --check
"$UV_BIN" run python scripts/generate_p008_schemas.py --check
"$UV_BIN" run python scripts/generate_p009_schemas.py --check
"$UV_BIN" run python scripts/generate_p006_fixtures.py --check
"$UV_BIN" run python scripts/generate_p006_fixtures_v2.py --check
"$UV_BIN" run python scripts/validate_p006_fixture_v2.py
"$UV_BIN" run python scripts/validate_p006_frozen_oracle.py
"$UV_BIN" run python scripts/validate_p006_frozen_oracle_v2.py
"$UV_BIN" run python scripts/validate_p006_worker_evidence.py
Rscript --vanilla -e 'invisible(parse(file="scripts/workers/p006-stylo-worker-v1.R")); cat("p006-worker-parse-ok\n")'
if [ "$(uname -s)" = "Linux" ]; then
  "$UV_BIN" run python scripts/validate_p006_worker_parity.py
  "$UV_BIN" run python scripts/validate_p006_scientific_handoff.py
else
  printf '%s\n' "p006-worker-and-handoff-skipped: canonical Linux execution required"
fi
"$UV_BIN" run pytest --cov=delta_lemmata --cov-report=term-missing
"$UV_BIN" run python scripts/check_metadata.py
"$UV_BIN" run python scripts/validate_records.py
"$UV_BIN" run python scripts/scan_repository.py
Rscript --vanilla -e 'invisible(parse(file="scripts/oracles/p006-direct-stylo-v1.R")); cat("p006-oracle-parse-ok\n")'
Rscript --vanilla -e 'source("renv/activate.R"); stopifnot(as.character(getRversion()) == "4.5.2"); stopifnot(as.character(packageVersion("renv")) == "1.2.3"); stopifnot(as.character(packageVersion("stylo")) == "0.7.71"); stopifnot(as.character(packageVersion("jsonlite")) == "2.0.0"); invisible(capture.output(status <- renv::status())); stopifnot(isTRUE(status$synchronized)); cat("r-lock-ok stylo-namespace-load-deferred\n")'

printf '%s\n' "verify-ok"
