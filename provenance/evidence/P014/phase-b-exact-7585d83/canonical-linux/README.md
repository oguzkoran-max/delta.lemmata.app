# Canonical Linux Failure Evidence

This content-free browser record was printed by GitHub Actions push run
`29566681494`, verify job `87840753618`, from clean exact commit
`7585d83a45dbc35580fc85346c2bdc731c07c720`.

The full source and metadata gate passed before the browser gate. The hardened
container job also passed. The real R/stylo browser flow then failed closed at
result publication: the terminal job had succeeded and its scientific result
was present and confirmed, but WORK had already been removed, so no public
result view or export could be created. The browser gate returned nonzero and
the remaining success-only CI steps were skipped.

The JSON was transcribed without payload content from the delimited evidence
block in the immutable GitHub job log. It is historical failure evidence, not a
successful acceptance record. Run `shasum -a 256 -c SHA256SUMS` in this
directory to verify it.
