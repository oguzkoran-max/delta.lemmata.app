# P014 Main Image Publication Checkpoint

## Current State

Owner-approved Phase B pull request `#8` was merged with a normal merge commit.
The exact release source is
`25fc2cadbba2147db6c7767e802088706a305f28`. Main CI run `29597139461`
passed both verify and container jobs. Publication run `29597615330` rebuilt
and re-gated that source, then published the private immutable manifest:

```text
ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:eb0c13a77dc39af8cf4dbfdadc811dd3bbe1f0b3d0381b15e140f5367ce9a54d
```

No mutable `latest` tag was published. The exact tag is not an authorised
deployment identity; deployment must use and verify the digest.

## Boundary

No VPS, Docker, Caddy, DNS, Lemmata, or public-route change was made during this
checkpoint. The image is not signed or attested. Target-host readback,
localhost-only installation, live load/coexistence, rollback, and both owner
decision gates remain open. P014 remains `in-progress`.

## Next Ordered Step

1. Merge this evidence-only record through normal CI.
2. Run a fresh read-only target-host inventory and Lemmata baseline.
3. Prepare the accepted Docker runtime without touching Caddy or DNS.
4. Pull and verify the exact digest, then start Delta only on
   `127.0.0.1:8502`.
5. Prove external denial and present the pre-Caddy evidence to Oğuz Koran.
6. Do not add the public Caddy route without Oğuz Koran's separate explicit
   authorisation.

## Canonical Evidence

- `provenance/evidence/P014/phase-b-main-immutable-image-publication.md`
- `provenance/runs/RUN-20260717-0003.json`
- `provenance/tickets/P014.json`
