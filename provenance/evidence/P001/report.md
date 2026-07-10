# P001 Acceptance Report

**Ticket:** P001  
**Run date:** 2026-07-10  
**Scope:** Repository, locks, metadata, schemas, provenance, CI, security, and SBOM scaffold  
**Product workflows:** Not implemented

## Result

All seven P001 acceptance criteria passed within their stated scope. The
repository baseline was committed as `26131a8`, restored from a new Git clone,
and is ready for P002.
This report does not claim that the container has been built, that `stylo`
analysis works, or that any scientific result has been validated.

## Repository Boundary

- Delta is an independent Git repository with default branch `main`.
- The parent academic-assistant repository ignores the complete Delta directory.
- Delta is not a submodule and has no remote yet.
- MIT covers software code only; corpus and edition rights remain asset-level.

## Locked Baseline

| Component | Value |
|---|---|
| Python | 3.13.9 |
| uv | 0.11.28 |
| Streamlit | 1.59.1 |
| Pydantic | 2.13.4 |
| jsonschema | 4.26.0 |
| R | 4.5.2 |
| renv | 1.2.3 |
| stylo | 0.7.71 |
| jsonlite | 2.0.0 |
| Linux base | `rocker/r-ver:4.5.2` |
| Base manifest digest | `sha256:fd4ccdd3a4a6f7ef805e2daeee2a0fe3bf126bc231f36351223baecf5a595a4c` |

Lock hashes:

- `uv.lock`: `5d435ec968063c0f4c7120e8974f1e94aef4b421eac265d52e0d7d4ce8ce450e`
- `renv.lock`: `bb792d224470650053412194edc35f3fd866673bd78d30ca756fcec3ad86ea1d`

Two consecutive frozen bootstrap runs left both lockfiles byte-identical.

## Acceptance Evidence

| Gate | Result | Evidence |
|---|---|---|
| P001-AC-01 clean checkout command | Passed | New Git clone of `26131a8`; `./scripts/bootstrap.sh`, then full verify; zero working-tree changes |
| P001-AC-02 quality checks | Passed | Ruff format/lint, strict mypy, 24 pytest tests, 100% Python source coverage |
| P001-AC-03 lock consistency | Passed | Second bootstrap; both SHA-256 values unchanged; `renv` synchronized |
| P001-AC-04 PromptEvent semantics | Passed | Native request hash and summary-only response separation validated by schema/tests |
| P001-AC-05 HumanDecision separation | Passed | Two accepted human decisions; AI assistance stored separately; negative tests pass |
| P001-AC-06 repository hygiene | Passed | Custom path/secret/corpus scan zero; detect-secrets zero after structural allowlist |
| P001-AC-07 pinned container references | Passed with disclosed limitation | Base and CI actions digest/SHA pinned; Docker build not locally run |

## Security and Supply Chain

- 44 runtime Python dependencies audited; zero known vulnerabilities reported.
- Reproducible Python CycloneDX SBOM contains 95 environment components.
- R CycloneDX SBOM derived from `renv.lock` contains 18 components.
- `detect-secrets` initially reported only cache tags, pinned action SHAs, the
  `renv` bootstrap MD5, and a known SHA-256 test vector. After narrow structural
  allowlisting, findings are zero. High-entropy scanning remains enabled.
- GitHub Actions are pinned to commit SHAs recorded in
  `containers/ci-actions.lock.json`.
- The Docker tag, manifest-list digest, and linux/amd64 child digest are recorded
  in `containers/base-images.lock.json`.

Generated SBOM, audit, scanner, environment, and checksum files are intentionally
ignored because some contain machine-local installation paths. Their aggregate,
path-free results are recorded in `environment-summary.json` and this report.

## Failures Preserved

1. First `uv lock` failed because modern setuptools rejects a legacy license
   classifier when a PEP 639 license expression exists. The classifier was removed.
2. First strict mypy run rejected the package without `py.typed`; the marker and
   package-data rule were added.
3. Second mypy run found missing `jsonschema` stubs; a locked stub package was added.
4. First repository scan produced a false positive from its own negative API-key
   test; the regex was narrowed without disabling secret detection.
5. First supply-chain test assumed a GitHub action had no subpath and every uv
   workspace record had a version; both assumptions were corrected.
6. `pip-audit` could not consume `uv.lock` directly. The audit now uses a frozen,
   hash-bearing requirements export from uv.
7. Local `stylo` namespace loading fails because the current macOS R/Tcl-Tk build
   requires XQuartz. P001 verifies installation and lock state only. P006 must test
   actual `stylo` execution and parity in the canonical Linux container.
8. The first machine-readable Run record contained a manually truncated SHA-256
   value. Schema validation rejected the 62-character value before acceptance; the
   digest was reread from the artifact and corrected.
9. A verification run scanned generated SBOM files and reported machine-local
   installation paths. The scan was corrected to exclude the ignored, derived
   `provenance/evidence/*/generated/` directory while retaining checks over every
   versionable source and evidence summary.

## Open Verification

- Docker is absent on the current Mac, so the pinned container has not been built.
- CI has not run because the repository has no GitHub remote.
- `stylo` computation and parity are P006 responsibilities.
- No DOI, SWHID, GitHub URL, release tag, or public release has been invented.

These are disclosed limitations, not hidden passes. P001's container criterion is
limited to pinned references and truthful build status.
