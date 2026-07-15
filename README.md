# Delta

Delta is a scholar-led, uncertainty-aware stylometry workbench for literary and
digital humanities research. Its supported workflows are designed to run without
requiring users to first learn or write R or Python code, while keeping corpus
choices, parameters, limitations, and rerun evidence visible.

**Current stage:** P001-P006 are complete. P007 has passed its technical gates
and remains open only for the integrated owner warning-language walkthrough. The
minimum public-alpha Guided path in P008-P009 now validates bounded TXT or ZIP
input, documents corpus metadata and rights, prepares a private ephemeral corpus,
runs four fixed Classic Delta comparisons through R `stylo`, and presents a
raw-text-free result view with explicit interpretation limits. Research Mode,
the full three-purpose workflow matrix, benchmark and calibration claims, the
Pinocchio worked example, complete FAIR packaging, and production deployment
remain outside this validated minimum-alpha boundary.

## Product Boundaries

- R `stylo` is the canonical analysis engine.
- Python and Streamlit provide orchestration and the browser interface.
- v0.1 has no runtime AI, external LLM API, login, analytics, or permanent project storage.
- Delta does not prove authorship, estimate confidence, or remove corpus confounds.
- Delta does not align versions, compute textual diffs, annotate variants, or create editions.

## Development Method

Delta is developed through scholarly vibe coding: a scholar-led, evidence-gated
form of AI-assisted research software development. Oğuz Koran owns the research,
method, acceptance, and scientific claims; Claude and Codex support implementation,
testing, documentation, and review. See
`decisions/ADR-0008-scholarly-vibe-coding.md`.

## Bootstrap

Prerequisites:

- CPython 3.13
- R 4.5
- POSIX shell

Install the locked Python and R environments:

```bash
./scripts/bootstrap.sh
```

Run the full verification suite:

```bash
./scripts/verify.sh
```

Development creates a process-private temporary runtime automatically. Production
requires a pre-created private runtime directory and three separately generated
secrets; see `.env.example`. These values must never be committed.

The canonical scientific environment is a pinned Linux x86_64 OCI image and is
verified in GitHub Actions. Production deployment and shared-VPS isolation remain
unverified until the minimum P014 activation gates pass. Container execution is
not repeated on the current Mac because Docker is not installed.

The staged public-alpha deployment and rollback procedure is documented in
`deploy/public-alpha/README.md`. That runbook does not authorize a live rollout:
the exact commit, container gate, read-only host inventory, coexistence checks,
and owner activation decision must pass in order.

## Canonical Project Documents

- `START_HERE.md`: minimal agent entry point
- `DEVELOPMENT_CONTRACT.md`: product, method, FAIR, security, and paper contract
- `docs/development/roadmap-P001-P015.md`: acceptance-gated implementation plan
- `docs/research/claim-evidence-matrix.md`: claims and evidence gates
- `docs/security/threat-model.md`: security, rights, and epistemic threats
- `deploy/public-alpha/README.md`: staged deployment, coexistence, and rollback runbook
- `SESSION_HANDOFF.md`: current stage and next action

## Citation and License

Software citation metadata is in `CITATION.cff` and `codemeta.json`. Code is
released under the MIT License. Corpora, editions, transcriptions, annotations,
and other data assets retain their own asset-level rights records and are not
automatically covered by the software license.
