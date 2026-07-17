# P014 Phase B Main and Immutable Image Publication

## Scope

This record binds the owner-approved Phase B integration on `main` to one
private, content-addressed GHCR application image. The exact release source is
the normal merge commit
`25fc2cadbba2147db6c7767e802088706a305f28`, created by pull request `#8`.

This publication did not connect to the target VPS, install Docker, change the
Lemmata service, edit Caddy or DNS, expose port `8502`, or activate
`delta.lemmata.app`. P014 remains `in-progress`.

## Merge and Main-CI Chain

- Pull request: <https://github.com/oguzkoran-max/delta.lemmata.app/pull/8>
- Merge strategy: normal merge commit; the Phase B implementation, remediation,
  retained failures, independent reviews, and FAIR evidence were not squashed.
- PR merged: `2026-07-17T16:41:18Z`.
- Exact merged source:
  `25fc2cadbba2147db6c7767e802088706a305f28`.
- Main CI run: `29597139461`, event `push`, branch `main`, result `success`.
- Main verify job: `87940183844`, result `success`.
- Main container job: `87940183862`, result `success`.

Main-CI URL:
<https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29597139461>

The exact main SHA passed source, schema, metadata, record, installed-wheel,
real R/`stylo` browser, SBOM, dependency, secret, canonical Linux image, and
hardened public-alpha stack gates before image publication began.

## Publication Run

- Workflow: `P014 publish immutable image`.
- Run: `29597615330`.
- Job: `87941738365`.
- Trigger: manual `workflow_dispatch` from `main` with the exact source SHA.
- Created: `2026-07-17T16:48:37Z`.
- Job started: `2026-07-17T16:48:43Z`.
- Job completed: `2026-07-17T16:54:09Z`.
- Result: `success`.

Publication URL:
<https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29597615330>

The job checked out the requested source, required a successful CI run for that
SHA, restored the locked browser environment, built the Linux amd64 image,
created fresh private runtime secrets, re-ran the hardened stack gate, and
published only the exact-commit tag.

## Repeated Pre-Publish Gate

- Application image ID:
  `sha256:0228082e41611b86b37d09f3a77349ecb40086ee205c3c9c7011ae45938b2aa4`.
- Pinned gateway runtime image ID:
  `sha256:acffd179eaca40d7d73dc928ed314730fc7110a2f34c03f295245c344c90d037`.
- Hardened stack health, hostile-request, runtime-control, denied-egress,
  browser, and cleanup gates passed again immediately before publication.
- The temporary registry login and generated secrets were not retained in this
  evidence.

## Registry Identity

The workflow published the exact source tag:

```text
ghcr.io/oguzkoran-max/delta.lemmata.app:sha-25fc2cadbba2147db6c7767e802088706a305f28
```

The only authorised deployment reference is the content-addressed manifest:

```text
ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:eb0c13a77dc39af8cf4dbfdadc811dd3bbe1f0b3d0381b15e140f5367ce9a54d
```

The registry reported manifest size `5145` bytes. No mutable `latest` tag was
published. The exact-commit tag is a locator and may be mutable at the registry
level; the target host must pull and verify the digest above rather than trust
the tag alone.

## Independent Boundary Check

The publication workflow proves that a successful CI run existed for the
requested SHA. For this release, the operator also independently verified that:

- `HEAD`, local `main`, and `origin/main` were the same exact source SHA;
- CI run `29597139461` was a successful `push` run on branch `main` for that
  exact SHA; and
- publication run `29597615330` used the same exact SHA.

This additional check matters because the current workflow does not itself
require the prerequisite CI run to be a `main`-branch `push` event. The current
release chain is accepted because that condition was separately observed and
recorded; the workflow-level enforcement gap remains a future hardening item.

## Supply-Chain Limitations

- The image is private and content-addressed, but it is not cryptographically
  signed and has no SLSA/in-toto provenance attestation.
- The GitHub-hosted runner is named by the workflow but not pinned by an
  immutable runner-image digest.
- The publication job records the pushed digest but does not perform a second,
  independent registry readback after logout.
- The target-host pull verifier must compensate by checking the pulled manifest
  and local image identity against the exact digest before any service starts.
- These limitations prevent claims of signed supply-chain provenance,
  tamper-proof authorship, production maturity, or complete FAIRness.

## Evidence-Integration Verification

The evidence-only working tree was checked before review:

1. The first `./scripts/verify.sh` attempt stopped before any test because the
   disposable worktree did not contain a local `uv` executable.
2. The second attempt used the canonical locked Python environment. All 1,725
   applicable tests passed with one declared canonical-Linux-only skip and 100%
   measured coverage, but the final R lock check stopped because the disposable
   worktree had bootstrapped only `renv`, not the canonical `stylo` library.
3. The final attempt explicitly linked the disposable worktree to the canonical
   locked Python and R libraries. It passed 1,725 tests with one declared
   canonical-Linux-only skip, 11,692 measured statements, 3,050 measured
   branches, 100% measured coverage, metadata, all 116 records, repository
   scanning, the R oracle parse, and the R lock check, ending with `verify-ok`.

The two stopped attempts were environment-path failures rather than application
or record failures. They were corrected without weakening or skipping a gate.

## Acceptance Mapping

- P014-AC-01 and P014-AC-07 are strengthened for the merged Phase B source by
  exact main CI, repeated hardened gates, and the immutable registry identity.
- P014-AC-05 remains pending for the complete live deployment profile.
- P014-AC-08 remains pending until a fresh target-host baseline, isolated
  localhost-only installation, and content-free host evidence pass.
- P014-AC-09 and P014-AC-10 remain pending because concurrent load,
  Lemmata-coexistence, reboot/cleanup, rollback, and owner acceptance have not
  occurred.

## Claim Boundary

This evidence proves that one exact merged and green source commit produced a
private content-addressed application image after the declared publication
gates passed. It does not prove target-host pullability, host readiness, public
TLS reachability, Lemmata coexistence under load, rollback, general usability,
FAIR completeness, publication readiness, or owner acceptance of public-alpha
activation.
