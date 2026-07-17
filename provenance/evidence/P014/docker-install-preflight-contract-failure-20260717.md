# P014 Docker Install Preflight Contract Failure

Date: 2026-07-17
Run: `RUN-20260717-0004`
Outcome: failed safely before host mutation

## Scope

This record covers the fresh target-host baseline and the first guarded Docker
installer dispatch for the owner-authorized localhost-only staging sequence. It
does not cover a Docker installation, Delta image pull, Delta service start,
Caddy edit, DNS change, or public activation.

The application release source remained
`25fc2cadbba2147db6c7767e802088706a305f28`, with immutable private image:

```text
ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:eb0c13a77dc39af8cf4dbfdadc811dd3bbe1f0b3d0381b15e140f5367ce9a54d
```

No image was pulled or started in this run.

## Fresh Read-Only Baseline

The exact operations tree was staged root-only at:

```text
/root/p014-ops-25fc2cadbba2147db6c7767e802088706a305f28
```

`p014_host_gate.py pre-docker` passed with schema `1.3.0` at
`2026-07-17T17:35:21.053753Z`. The content-free record reported:

- Ubuntu 26.04 `resolute`, x86_64, 2 CPUs;
- 3,814 MiB total and 2,339 MiB available memory, no swap;
- 32,449 MiB free root disk;
- zero current memory-pressure and recent kernel-OOM markers;
- active Caddy and Lemmata, inactive Docker and Delta;
- Lemmata 20/20 healthy responses, median 58.394 ms, p95 154.422 ms,
  zero restarts, and 1,118,261,248 bytes current memory;
- `127.0.0.1:8501` present and port `8502` absent;
- disabled IPv4/IPv6 forwarding and empty observed nftables, iptables, and
  ip6tables baselines;
- unchanged Caddyfile SHA-256
  `ec824143747f51a2b571de61ae87bf06714e7be76684d5d9e665bb653116c9e5`;
- Docker binary, service, official key/source, package set, and data roots absent.

The exact raw record is retained as
`provenance/evidence/P014/live-20260717/pre-docker.json`, SHA-256
`d781e6067992bea14b1c3e0a833fab81efbc74f6b4bdd11ea25e5c2065ddf1bc`.

## Rejected Installer Dispatch

Following the then-current Phase 3 runbook, the operator created a separate
`pre-mutation` observation and passed it to the installer as `--preflight`.
That observation passed at `2026-07-17T17:36:39.378310Z`; Lemmata remained
20/20 healthy, Caddy and Lemmata remained active, Docker and Delta remained
inactive, and port `8502` remained absent. Its exact raw record is retained as
`provenance/evidence/P014/live-20260717/pre-mutation.json`, SHA-256
`415ab6d10aaae33aeb4fe3a6221c4d6f017a60b420917506cf2717ba4384a1a6`.

The installer then returned exit `1` with:

```text
P014_DOCKER_INSTALL_GATE_PHASE_INVALID
```

The rejection was correct. The installer requires the accepted `pre-docker`
baseline, copies it into its root-only transaction directory, validates the
captured firewall inputs, and generates its own fresh `pre-mutation` observation
immediately before the first package change. The runbook and its deployment
validator incorrectly required an externally generated `pre-mutation` file.

## No-Mutation Verification

A post-failure read-only recheck confirmed:

```text
docker_binary=absent
docker_service=inactive
caddy_service=active
lemmata_service=active
delta_service=inactive
path_absent=/etc/apt/keyrings/docker.asc
path_absent=/etc/apt/sources.list.d/docker.sources
path_absent=/var/lib/docker
path_absent=/var/lib/containerd
path_absent=/root/p014-host-evidence/docker-change-20260717
docker_packages=absent
port_8501=1
port_8502=0
caddy_hash=ec824143747f51a2b571de61ae87bf06714e7be76684d5d9e665bb653116c9e5
pre_docker_evidence=present
pre_mutation_evidence=present
```

This recheck was captured in the operator transcript and summarized here; no
separate native JSON was created for it. The two native gate JSON files above
remain the raw retained artifacts. No package, repository key/source, Docker
data root, installer transaction directory, service, listener, Caddyfile, DNS
record, or public route was changed.

## Root Cause and Correction

The implementation contract is intentionally:

```text
accepted pre-docker baseline
  -> installer-owned firewall verification
  -> installer-owned fresh pre-mutation observation
  -> first package mutation
```

The correction therefore changes the runbook and deployment validator to pass:

```text
--preflight /root/p014-host-evidence/pre-docker.json
```

The installer is not weakened or changed. Regression tests now require the
Phase 3 block to use `pre-docker`, reject `pre-mutation` as installer preflight,
and leave creation of the final pre-mutation observation inside the guarded
transaction.

## Decision Boundary

The failed run is retained rather than rewritten or superseded. A later
successful Docker installation must receive a new Run ID. P014-AC-08 remains
pending because an accepted post-Docker inventory does not yet exist. The
existing owner authorization permits a corrected official-Docker preparation
and localhost-only Delta staging after normal review and green CI. It still does
not authorize Caddy, DNS, or public-route changes; the separate pre-Caddy owner
gate remains mandatory.
