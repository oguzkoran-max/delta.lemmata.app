# P003 Exact-Commit Clean-Clone Verification

## Source

- Commit: `60bb93e4554cf7fa2827014b719cc8eb427a9ada`
- Branch at clone time: `codex/p003-secure-ingestion`
- Clone method: `git clone --no-local --branch codex/p003-secure-ingestion`
- Temporary clone: `/tmp/delta-p003-replay.ddRVkN`
- Started: `2026-07-11T09:48:17Z`
- Ended: `2026-07-11T09:51:29Z`
- Source status before dependency installation: clean
- Source status after verification and before generated browser evidence: clean

No source file was edited in the clone. `./scripts/bootstrap.sh` installed the
pinned uv tool into the clone, then installed Python and R dependencies from
`uv.lock` and `renv.lock`. R artifacts were linked from the host's renv cache where
available.

## Environment

| Component | Value |
|---|---|
| macOS | 26.5.1 |
| Architecture | arm64 |
| Python | 3.13.9 |
| uv | 0.11.28 |
| R | 4.5.2 |
| stylo | 0.7.71 |
| Streamlit | 1.59.1 |
| Playwright | 1.61.0 |
| Chromium | 149.0.7827.55 |

## Command Record

1. `./scripts/bootstrap.sh`
   - Exit: 0
   - Result: installed uv 0.11.28, 98 locked Python packages, and ten locked R
     packages, including stylo 0.7.71 and jsonlite 2.0.0.
2. `./scripts/verify.sh`
   - Exit: 0
   - Result: 232 tests passed; 900 statements and 218 branches reached 100%;
     metadata, provenance, repository, and R lock checks passed.
3. `.venv/bin/python scripts/browser_audit_p003.py --output provenance/evidence/P003/clean-clone-browser`
   - Exit: 0
   - Result: six viewport checks and synthetic TXT, CSV, rejection, and ZIP
     interactions passed with no console messages or observed external host.
4. `.tools/uv/bin/uv build --wheel --out-dir /tmp/delta-p003-wheel-replay`
   - Exit: 0
   - Result: built `delta_lemmata-0.0.0.dev0-py3-none-any.whl`.

## Package Check

- Wheel SHA-256:
  `a014c894a76afbb223ae2f1a3beefef2d8a475c0d718c95ac87db31fb3afec9f`
- Source limit profile SHA-256:
  `e473f3fb15097bfdcade400e5b6ef352ab96248a28e8b34a9b0e8e9279928f58`
- Wheel-contained limit profile SHA-256:
  `e473f3fb15097bfdcade400e5b6ef352ab96248a28e8b34a9b0e8e9279928f58`
- Result: the versioned ingestion policy is present and byte-identical in the
  built wheel.

A preliminary manual replay produced a different whole-wheel SHA-256 from the same
commit while preserving the same policy hash. P003 therefore records each build
instance but does not claim bit-for-bit reproducible wheel packaging; that release
property remains a later reproducibility gate.

## Retained Preliminary Failures

Before using the canonical bootstrap script, a separate fresh clone recorded two
failed commands: bare `uv sync` exited 127 because uv was absent from host `PATH`,
and the first `verify.sh` reached the R gate before clone-local `renv::restore`.
These failures motivated the final replay through `./scripts/bootstrap.sh` and are
retained in `failure-log.md` and `test-summary.json`.

## Scope

This is an exact-source clean-clone replay on the same Mac, not an independent
machine or clean-room reproduction. Global pip, uv, and renv caches may supply
locked artifacts. Browser request observation is not a packet capture. Bit-for-bit
wheel reproducibility is not established.
