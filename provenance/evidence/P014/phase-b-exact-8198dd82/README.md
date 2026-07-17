# Exact-SHA Phase B Failure Evidence

Exact commit `8198dd82a30af2f6c89301ab38189e1b1b0b4fe9` corrected the
premature-WORK-cleanup defect found at `7585d83`, but it did not close the
workflow. This directory preserves the next fail-closed result instead of
overwriting the history.

GitHub Actions push run `29581928666` and pull-request run `29581931331`
passed the source, metadata, test, installed-wheel, and hardened-container
gates. Both real R/stylo browser jobs failed at the result UI gate. The
scientific result and public result view were present, the export was available,
and input/WORK cleanup was verified, but the session retained the pre-cleanup
`finalizing` presentation and never exposed the result UI.

Independent exact-SHA review also identified an unbound global-queue/session
race and the absence of a bounded retry window when projection failed. These
issues are remediated only by the later code commit recorded in the superseding
Run; this directory is not acceptance evidence.
