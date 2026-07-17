# P014 Docker Post-Install Gate and Rollback Integration Failure

Date: 2026-07-18 (Europe/Istanbul)
Run: `RUN-20260718-0001`
Outcome: Docker installation rejected by a false package-origin result; automatic
rollback removed Docker but required a guarded manual firewall completion

## Scope

This record covers the second owner-authorized Phase 3 attempt on the shared
Lemmata host. The exact operations source was commit
`748d3fdc688302d9b373557e030cf06bb39d78a1`, archived with SHA-256
`00f3e78936a77511ede0120b54150bb2cf129629d90421201f101e7018cc5c75`.
The immutable Delta application image remained:

```text
ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:eb0c13a77dc39af8cf4dbfdadc811dd3bbe1f0b3d0381b15e140f5367ce9a54d
```

The image was not pulled or started. Delta, Caddy, DNS, and the public route
were not changed.

## Accepted Baseline

The fresh `pre-docker` gate passed at `2026-07-17T21:46:25.894945Z`:

- Caddy and Lemmata were active; Docker and Delta were inactive;
- Lemmata returned 20/20 healthy responses with median 56.711 ms and p95
  130.160 ms;
- Lemmata had zero restarts and retained start identity `487847582`;
- 2,359 MiB memory was available, swap was absent, and no new listener was
  present;
- IPv4 and IPv6 forwarding were both zero;
- nftables, iptables, and ip6tables captures were all exactly empty, each with
  SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

The installer-owned `pre-mutation` gate also passed at
`2026-07-17T21:48:25.283264Z`. Lemmata again returned 20/20 healthy responses,
had zero restarts, and retained the same process start identity.

## Post-Docker Failure

The installer added only the fixed official Docker package set:

```text
containerd.io=2.2.6-1~ubuntu.26.04~resolute
docker-buildx-plugin=0.35.0-1~ubuntu.26.04~resolute
docker-ce=5:29.6.2-1~ubuntu.26.04~resolute
docker-ce-cli=5:29.6.2-1~ubuntu.26.04~resolute
docker-compose-plugin=5.3.1-1~ubuntu.26.04~resolute
```

The retained repository evidence had the expected Docker key fingerprint
`9DC858229FC7DD38854AE2D88D81803C0EBFCD88`, a valid source profile, Docker
Engine 29.6.2, and Compose 5.3.1. Nevertheless, the post-install gate failed at
`2026-07-17T21:48:45.628616Z` with only:

```text
P014_DOCKER_PACKAGE_ORIGIN_INVALID
```

The installer deliberately used a private APT list directory inside its
root-only state directory. The host gate's `apt-cache policy` command selected
the same installed candidate versions but consulted the host's unrelated
default APT lists, so all five `official_candidates` flags were false. This was
a verification-path defect, not evidence of an unofficial package install.

Lemmata remained active, returned 20/20 healthy responses with p95 61.219 ms,
had zero restarts, and retained the same start identity. No Delta listener or
service existed.

## Automatic Rollback Failure

The armed rollback removed every Docker package, repository file, runtime data
root, binary, and service, then restored forwarding to zero. Its post-rollback
gate at `2026-07-17T21:49:00.372080Z` failed only with:

```text
P014_FIREWALL_NOT_RESTORED
```

The original firewall captures were valid but empty. Passing an empty file to
`iptables-restore` or `ip6tables-restore` is a no-op; it does not delete the
Docker-created nftables tables. The retained residual contained only Docker
chains and bridge/NAT policy. Caddy and Lemmata were active, Lemmata returned
20/20 healthy responses with p95 62.176 ms, and no Docker package or service
remained.

## Guarded Manual Completion

Before any manual rule change, the residual nftables ruleset was retained as
`live-20260718/firewall-nftables.rollback-residual`. The three accepted baseline
captures were rechecked as byte-empty and the residual was inspected as
Docker-only. The operator then flushed that residual ruleset and reran the
existing guarded rollback.

The final `post-rollback` gate passed at `2026-07-17T22:06:18.010838Z`:

- Docker packages, binary, service, key/source, and runtime roots were absent;
- Caddy and Lemmata were active, while Delta was inactive;
- Lemmata returned 20/20 healthy responses with median 58.812 ms and p95
  62.023 ms;
- Lemmata had zero restarts and retained its original start identity;
- forwarding was zero and all three firewall captures again exactly matched
  the empty baseline;
- the listener set and Caddyfile identity remained unchanged.

The deployment attempt therefore ended safely but unsuccessfully. No public
Delta state was created.

## Corrections

The retained implementation correction is intentionally narrow:

1. post-Docker and Delta-idle host gates must receive the installer's absolute
   private APT list directory and use it for package-origin policy;
2. rollback must preserve firewall residuals before restoration;
3. when all three already-validated baseline captures are exactly empty,
   rollback must flush the Docker-created nftables ruleset before proving the
   empty baseline;
4. non-empty baselines continue to use the captured iptables and ip6tables
   restore inputs;
5. runbook and deployment validators must enforce these contracts;
6. regression tests must cover private APT policy, empty-baseline flush,
   non-empty restore, and immutable residual evidence.

No gate, source-origin requirement, rollback comparison, or Lemmata protection
is weakened.

## Retained Raw Evidence

The content-free raw evidence is retained under
`provenance/evidence/P014/live-20260718/`:

| Artifact | SHA-256 |
|---|---|
| `pre-docker-20260718-r2.json` | `747775d426d1fd3fa3114bfb2fefc56f2542782ca814d599ef8e4931254ff01c` |
| `transaction-pre-docker-20260718-r2.json` | `747775d426d1fd3fa3114bfb2fefc56f2542782ca814d599ef8e4931254ff01c` |
| `transaction-pre-mutation-20260718-r2.json` | `dc0c03b5543cfd4142641553829930a0eb7d7e27e8b9ad692307c81732cedcb4` |
| `post-docker-20260718-r2.json` | `586d90a77db0ffb295725e206e32fa0acf5f20ddb04d4e6450eb4ad4b49b7f59` |
| `post-rollback-20260718-r2.json` | `3d470eecc86dea32eab80cfa0045f0df3caa8d64ebe33a1e7965f3095c4e2ed3` |
| `post-rollback-manual-20260718-r2.json` | `2d36d30174213ec2d82ef9e0bc8d410ca8011014fcc32f58ff3e45812569b5d8` |
| `installed-packages.txt` | `57574621a1db905d7b5ad77d427763578d644a59ae1fb670f030f35dc472cc8a` |
| `firewall-nftables.rollback-residual` | `0e676b11805f4aa58c0f2dc56a5ae9186ea24d3f05f538b663a05d3a7ddfc24e` |
| each empty `firewall-*.before` capture | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## Decision Boundary

This failure remains permanent FAIR evidence. It does not satisfy P014-AC-08,
P014-AC-09, or P014-AC-10. A third Phase 3 attempt is prohibited until the
correction receives full local verification, normal pull-request review, green
Linux CI, and green main CI. Caddy, DNS, and public activation remain separately
unauthorized.
