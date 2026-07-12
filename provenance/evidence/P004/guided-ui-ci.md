# P004 Guided UI GitHub CI

Date: 2026-07-12

Status: passed; P004 human acceptance is not claimed.

## Verified Commit

- Commit: `4c3bb8ae0bf7690a64122613c58f80d7a831d6c4`
- Workflow: `CI`
- Run: `29190917436`
- URL: <https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29190917436>
- Trigger: push to `codex/p004-metadata-rights`
- Created: `2026-07-12T11:29:32Z`
- Completed: `2026-07-12T11:32:17Z`
- Conclusion: `success`

## Jobs

### Verify

- Job: `86645327027`
- Duration: 2 minutes 31 seconds
- Conclusion: `success`
- Passed steps: full-history source checkout, pinned uv/Python, pinned R,
  locked-environment restore, source/metadata/schema/record verification, SBOM
  generation, and dependency audit.

### Container

- Job: `86645327030`
- Duration: 2 minutes 40 seconds
- Conclusion: `success`
- Passed step: canonical Linux amd64 image build.

## Interpretation Boundary

This closes the GitHub CI gate for the implementation plus exact-commit provenance
linkage tree. It does not replace the local fresh-clone browser evidence, Safari or
VoiceOver walkthrough, rights terminology review, scientific computation,
production deployment, or Oğuz Koran's P004 acceptance decision.
