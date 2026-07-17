# Canonical Linux Harness Failure

This directory preserves the content-free browser evidence printed by GitHub
Actions push run `29584671661`, verify job `87898568867`, for clean exact
commit `a5b94d5ffe36d18e6d16399ef0c8be7cb671dbdb`.

The scientific lifecycle succeeded: the R/stylo job reached terminal
`succeeded`, its scientific result was present and confirmed, the public result
view and export were available, and input/WORK cleanup was verified. The CI job
still returned nonzero because the result-viewport aggregation attempted to read
the entry-only `uploader_context_pass` field and raised `KeyError`.

This is retained failure evidence, not acceptance evidence. The later exact
commit `dfce0299ce5674d2732870c6e286a5b6419e27aa` separates entry and result
surface contracts and must pass its own canonical Linux gates. Run
`shasum -a 256 -c SHA256SUMS` in this directory to verify the JSON.
