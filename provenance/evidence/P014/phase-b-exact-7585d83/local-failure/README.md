# Exact-SHA Local Failure Cleanup Evidence

This content-free browser record was produced from clean commit
`7585d83a45dbc35580fc85346c2bdc731c07c720` with synthetic inputs:

```text
.venv/bin/python scripts/browser_audit_p009.py \
  --output <temporary-output-directory> \
  --allow-noncanonical-local
```

The command returned nonzero at the documented macOS/noncanonical R-worker
boundary. The failure is the expected fail-closed outcome: no scientific result,
result view, or export was published. The lifecycle diagnostic records one
terminal failed job and verifies `input`, `work`, `result`, and `export` as
absent. `terminal_payload_cleanup_pass` is true.

This record does not substitute for canonical Linux success evidence. It exists
to prove the actual failed-worker cleanup path at the exact remediation SHA.
Run `shasum -a 256 -c SHA256SUMS` in this directory to verify the JSON.
