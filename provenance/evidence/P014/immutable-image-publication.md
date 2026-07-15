# P014 Immutable Application Image Publication

## Scope

This record binds the merged public-alpha source to one private, immutable GHCR
application-image manifest. It covers source commit
`8579e4e335cfa3ccbd1368588bf11d60dca08764`, the merge commit of pull request
`#4`, after main CI run `29426588836` passed both required jobs.

The publication did not install Delta, connect to the VPS, modify Caddy or DNS,
or activate a public route. P014 remains `in-progress` and public activation
remains prohibited.

## Prerequisite Chain

- Pull request: <https://github.com/oguzkoran-max/delta.lemmata.app/pull/4>
- Merge strategy: normal merge commit; the P007-P014 commit and provenance
  history was not squashed.
- Exact merged source:
  `8579e4e335cfa3ccbd1368588bf11d60dca08764`.
- Main CI: `29426588836`.
- Main verify job: `87390451573`, passed in 4 minutes 46 seconds.
- Main container job: `87390451645`, passed in 4 minutes 23 seconds.

The publication workflow independently required a successful CI run for the
requested full source SHA before it could build or push an image.

## Publication Run

- Workflow: `P014 publish immutable image`.
- Run: `29426974523`.
- Job: `87391795653`.
- Trigger: manual `workflow_dispatch` from `main` with the exact source SHA.
- Started: `2026-07-15T15:11:23Z`.
- Completed: `2026-07-15T15:17:35Z`.
- Result: passed.

Run URL:
<https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29426974523>

The job checked out the requested exact source, proved a clean source identity,
resolved prerequisite CI run `29426588836`, restored the locked environment,
and built the Linux amd64 application image with the merge commit as
`DELTA_BUILD_ID`.

## Repeated Pre-Publish Gate

Before publication, the workflow regenerated private runtime secrets and
re-ran the complete P014 hardened stack gate:

- Application runtime inspection passed with image ID
  `sha256:d03752691358a8aeb9387f90f97523c5779ecded0e63f8dc1d463b9fa5cddacf`.
- The pinned gateway runtime image ID remained
  `sha256:acffd179eaca40d7d73dc928ed314730fc7110a2f34c03f295245c344c90d037`.
- Stack health, hostile-request smoke checks, runtime controls, denied
  application egress, and cleanup passed.
- The TLS browser gate received 79 HTTP 200 responses, no blocked or failed
  request, and one successful WebSocket.
- Desktop 1280x900, mobile 390x844, and reflow 320x720 rendered both release
  labels without horizontal overflow.
- No browser console error or page error was observed.
- Both containers and both temporary networks were removed after the gate.

The retained markers were `p014-runtime-inspection-ok`,
`p014-stack-smoke-ok`, and `p014-runtime-gate-ok`.

## Immutable Registry Identity

Only the exact source tag was pushed:

```text
ghcr.io/oguzkoran-max/delta.lemmata.app:sha-8579e4e335cfa3ccbd1368588bf11d60dca08764
```

The deployment reference is the content-addressed manifest, not the tag:

```text
ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:596591039de86c39c976f984b5b22fc3fc040bd56a08c471cbb349aa6c84b4a2
```

The registry reported manifest size `5144` bytes. The mutable `latest` tag was
not published. The short-lived CI registry login was removed after the push;
no token value was retained in this evidence.

## Retained Attempt

An earlier dispatch against the feature branch returned HTTP 404 before a
workflow run was created. GitHub registers manually dispatched workflows from
the default branch, and the workflow did not yet exist there. The failed attempt
did not build or publish an image. The corrected sequence was:

1. pass PR CI;
2. merge without squashing provenance commits;
3. pass exact merge-commit CI on `main`;
4. dispatch the now-registered workflow for that exact merge commit.

This operational failure is retained rather than represented as a successful
publication attempt.

## Acceptance Mapping

- P014-AC-01: strengthened by the exact source, local image ID, private registry
  tag, and immutable registry manifest reference.
- P014-AC-07: strengthened by a second canonical Linux build and repeated
  hardened runtime, TLS browser, hostile-request, denied-egress, and cleanup
  gate immediately before publication.
- P014-AC-08: remains pending because the first target-host preflight stopped
  before host preparation and no accepted installation baseline exists.
- P014-AC-09 and P014-AC-10: remain pending because no live Delta-Lemmata load,
  restart, rollback, or owner acceptance has occurred.

## Claim Boundary

This evidence proves that one exact green source commit produced a private,
content-addressed application image after the declared pre-publication gates
passed. It does not prove that the image can be pulled by the target host, that
the target host is ready, that Delta is installed or publicly reachable, that
Lemmata is unaffected under concurrent load, that rollback works, or that Oğuz
Koran accepts activation. The image is not represented as signed, attested,
production mature, completely isolated, FAIR-certified, or publication ready.
