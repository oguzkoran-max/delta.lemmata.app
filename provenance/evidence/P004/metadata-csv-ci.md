# P004 Metadata CSV GitHub CI Evidence

**Commit:** `8dd85c1d3cd454c3b1a8227122ff73e136da87b0`

**Workflow run:** `29172847800`

**Conclusion:** `success`

**Run URL:**
`https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29172847800`

## Verify Job

- Job ID: `86596744188`
- Started: `2026-07-11T23:54:15Z`
- Completed: `2026-07-11T23:56:23Z`
- Conclusion: `success`
- Pinned uv/Python and pinned R setup passed.
- Locked Python and R environments restored successfully.
- Source, metadata, schema, test, and provenance verification passed.
- SBOM generation and dependency audit passed.

## Container Job

- Job ID: `86596744203`
- Started: `2026-07-11T23:54:20Z`
- Completed: `2026-07-11T23:56:58Z`
- Conclusion: `success`
- The canonical Linux amd64 image built successfully.

## Interpretation

This CI run verifies the same implementation commit recorded by
`RUN-20260711-0006`. It supersedes no historical Run record and does not turn P004
into a completed or human-accepted ticket. Streamlit metadata integration, browser
accessibility evidence, rights-questionnaire acceptance, scientific analysis,
deployment, and retention remain outside this CI result.

The earlier `93c9f50` failure email belongs to a superseded branch snapshot and does
not describe this run.

## Provenance-Link Commit CI

The follow-up evidence-link commit
`dc0000852e2df6a337ace81b368b86f305247516` also passed GitHub Actions run
`29173125607`:

- verify/SBOM/audit job `86597438543`: `success`;
- Linux amd64 container job `86597438556`: `success`;
- workflow completed at `2026-07-12T00:06:47Z`.

This second green run confirms that the reciprocal Ticket, Run, checksum, CI report,
and handoff records added after the implementation run also satisfy the repository
gates.
