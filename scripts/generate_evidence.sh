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

OUTPUT=provenance/evidence/P001/generated
mkdir -p "$OUTPUT"

"$UV_BIN" export --format requirements.txt \
  --no-dev \
  --no-emit-project \
  --frozen \
  --quiet \
  --output-file "$OUTPUT/runtime-requirements.txt"

"$UV_BIN" run cyclonedx-py environment .venv \
  --pyproject pyproject.toml \
  --output-reproducible \
  --output-format JSON \
  --output-file "$OUTPUT/python-sbom.cdx.json"
"$UV_BIN" run python scripts/normalize_python_sbom.py "$OUTPUT/python-sbom.cdx.json"

Rscript --vanilla scripts/generate_r_sbom.R "$OUTPUT/r-sbom.cdx.json"

"$UV_BIN" run pip-audit --requirement "$OUTPUT/runtime-requirements.txt" \
  --require-hashes \
  --format json \
  --output "$OUTPUT/pip-audit.json" \
  --progress-spinner off

"$UV_BIN" run detect-secrets scan --all-files \
  --exclude-files '(^|/)(\.git|\.tools|\.venv|\.mypy_cache|\.pytest_cache|\.ruff_cache|renv/library|renv/staging)/' \
  --exclude-lines '("commit": "[0-9a-f]{40}"|attr\(version, "md5"\)|assert sha256_text\("abc"\))' \
  --no-verify \
  > "$OUTPUT/detect-secrets.json"

"$UV_BIN" pip freeze --exclude-editable > "$OUTPUT/python-environment.txt"
Rscript --vanilla -e 'source("renv/activate.R"); sessionInfo()' > "$OUTPUT/r-session-info.txt"

shasum -a 256 \
  VERSION \
  uv.lock \
  renv.lock \
  CITATION.cff \
  codemeta.json \
  containers/base-images.lock.json \
  containers/ci-actions.lock.json \
  > "$OUTPUT/checksums.sha256"

"$UV_BIN" run python scripts/validate_generated_evidence.py "$OUTPUT"
shasum -a 256 -c "$OUTPUT/checksums.sha256"

printf '%s\n' "evidence-generated path=$OUTPUT"
