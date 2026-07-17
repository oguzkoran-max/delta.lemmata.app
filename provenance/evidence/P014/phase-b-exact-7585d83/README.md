# Exact-SHA Phase B Failure Evidence

This directory preserves the fail-closed evidence for exact commit
`7585d83a45dbc35580fc85346c2bdc731c07c720`. It is intentionally retained
after the lifecycle defect was corrected so the remediation history remains
auditable.

- `local-failure/` records the noncanonical macOS worker boundary. The job
  failed and every application-managed payload artifact was verified absent.
- `canonical-linux/` records GitHub Actions push run `29566681494`, verify job
  `87840753618`. The R/stylo job reached a confirmed scientific result, but the
  result projection was unavailable because maintenance removed WORK before
  publication finalization. Input and WORK were absent, the private scientific
  result remained present, no public result view or export was created, and no
  partial public result was presented.

Neither record is success evidence. Together they identify the lifecycle
regression that exact commit
`8198dd82a30af2f6c89301ab38189e1b1b0b4fe9` was created to remediate.
