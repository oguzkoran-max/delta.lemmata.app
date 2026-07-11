# CI Shallow-History Failure and Repair

## Observation

On 2026-07-11, Oğuz Koran reported repeated GitHub Actions failure emails. The
mail screenshot showed the `verify` job failing while the Linux `container` job
succeeded. The screenshot was inspected but is not retained in the repository
because it exposes personal mail-account identifiers and adds no evidence beyond
the GitHub run records.

Representative failed runs:

- P004 branch run `29165443362`, commit `e94ee3754e1759acf0dd93eff78e5b1d8c9e0f56`
- P004 branch run `29165815682`, commit `93c9f50`
- main run `29165214188`, P003 merge

The same infrastructure failure affected several earlier main, feature, and
Dependabot runs. It was not evidence that the application or container build was
broken.

## Failure Signature

The Linux job collected all 232 tests and failed only two record-integrity tests.
The first reported 61 unresolved historical commits, beginning with:

```text
P001: unresolved commit 26131a88a04d1d79ffe50d9eb9ee676d41c2072b
```

Input-artifact verification then failed because `git show <tested-commit>:<path>`
could not resolve those commits. The container job remained green.

## Root Cause

`actions/checkout` defaults to a one-commit shallow checkout. Delta's FAIR-oriented
record-integrity gate intentionally resolves historical Ticket and Run commit IDs
and recomputes input hashes from their tested commits. The local repository has
the complete history, so local verification passed; the GitHub runner did not have
the objects required to perform the same check.

## Repair

The `verify` checkout now sets:

```yaml
with:
  fetch-depth: 0
```

The container checkout remains shallow because the image build does not inspect
historical provenance. A regression test restricts the requirement to the verify
job and prevents accidental removal of full-history checkout.

Repair commit:

- `f7a75b024d188f24cd7877cd930b453dd2eedace`

Main integration:

- `0b0b3491bf9d3ad299099f7763752b661aaa9fc5`

## Verification

Local hotfix and post-merge verification:

- 233 tests passed
- 100% measured statement and branch coverage
- metadata, record-integrity, repository, supply-chain, and R-lock gates passed

GitHub hotfix branch run:

- Run `29167750356`
- `verify`: passed, including SBOM generation and dependency audit
- `container`: passed

GitHub main run:

- Run `29167865311`
- `verify`: passed in 2m32s
- `container`: passed in 2m34s

The failure is closed as a CI checkout-configuration defect. It does not supersede
or weaken the historical provenance checks.
