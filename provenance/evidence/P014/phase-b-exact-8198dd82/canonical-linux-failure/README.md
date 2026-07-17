# Canonical Linux Result-UI Failure

This content-free JSON is the exact delimited browser evidence printed by
GitHub Actions push run `29581928666`, verify job `87889442808`, for clean
commit `8198dd82a30af2f6c89301ab38189e1b1b0b4fe9`.

The record proves that the real R/stylo job succeeded, the scientific result
was confirmed, the public result view and export were present, and terminal
payload cleanup passed. The browser nevertheless remained on `Finalizing
analysis`, so the current workflow correctly returned nonzero rather than
claiming success.

The JSON was transcribed byte-for-byte from the immutable job log. Run
`shasum -a 256 -c SHA256SUMS` in this directory to verify it.
