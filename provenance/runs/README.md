# Run Records

Machine-readable test, security, benchmark, analysis, and rerun records live here.
P001 defines the schema; scientific analysis runs begin in later tickets.

## Configuration Hash Policy

Run schema `1.0.0` used `config_sha256`, a pathless digest whose referent was not
machine-readable. `RUN-20260710-0001` through `0004` used the SHA-256 of
`pyproject.toml`. Claude review Runs `RUN-20260710-0005` and `0006` instead used
the SHA-256 of `.streamlit/config.toml`. Both historical interpretations remain
unchanged as evidence of what was recorded; neither should be inferred without
its accompanying artifact list.

Run schema `1.1.0` deprecates and omits `config_sha256`. Every configuration is
recorded as an explicit `{path, sha256}` member of both `configuration_artifacts`
and `input_artifacts`. A `1.1.0` Run may supersede named fields or claims in an
older Run without deleting or rewriting that older record.

## Replay And Closure

A `1.1.0` Run records an exact command, working directory, replay level, and
limitations. Placeholders such as `<repo>` are not executable evidence. A Run
points to the already-existing commit it tested and never hashes its own JSON
record. Evidence manifests live outside the directory they cover so that they do
not recursively hash themselves. A closure commit does not attempt to include
its own future Git SHA; its Git history is the terminal anchor.
