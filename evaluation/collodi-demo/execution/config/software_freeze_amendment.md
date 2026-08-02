# Software-freeze amendment for DATA-COLLODI-DEMO-V1

- Amendment time (UTC): `2026-08-02T21:06:33Z`
- Upstream dataset-lock manifest SHA-256: `f740e4c57c11d376346d4c7a8cc5d23fbea5c28544167de3ee2f0d496f7f4292`
- Outcomes file SHA-256 at dataset lock: `135d2951d8df399d9f7e659209d3c876b1ca2cad5f4df8417f95b73e3321dd96`
- Frozen source commit: `31e09782ba07e6709cbdcca48bc9db22e6c49723`
- Frozen image: `ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa`
- Canonical request SHA-256: `0eb1c53ca5e1f930cd7a331cf13b6b090cf68083b8a16a0bb846c496160fe5f0`
- Results-blind preflight: `25/25 PASS`

This amendment closes the software-freeze gate that remained open when the
corpus was sealed. It does not alter the documents, cleaning decisions,
MFW grid, culling level, distance, display condition, seed, claim boundary,
or success criteria.

At the time of this amendment, no Collodi demo distance matrix, MDS
coordinate, cluster, parity outcome, or literary interpretation existed in
the execution directory. The four MFW cells were registered as
`ready_results_blind` before execution.

Execution is permitted only through the pinned workflow and only if the
preflight validator reports `ready_for_execution`. The results remain
inadmissible until the Delta worker and the independent direct-R oracle pass
the locked parity criteria for every MFW cell.
