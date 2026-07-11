# P002 Codex Correction: Failures And Rejected Evidence

1. Google Drive dehydrated tracked files after the branch switch. Reads and Git
   status processes blocked on `dataless` placeholders. Twenty-eight unchanged,
   tracked files were materialized from the exact `HEAD` Git objects. No modified
   file was overwritten.
2. The first browser harness targeted the segmented control as a button and then
   by a non-existent Streamlit test id. Live DOM inspection showed that Streamlit
   1.59.1 exposes the choices as radios. The harness now uses their actual role.
3. Streamlit Material Symbol ligatures (`table_view`, `arrow_forward`, and
   `play_arrow`) appeared inside disabled-button accessible names. Icons were
   removed from those unavailable controls so their names remain concise and
   include the reason.
4. A first replay of `b53e3087...` passed, but its browser report still promised a
   separately recorded real zoom test. That wording was rejected. Commit
   `05e7b01c...` explicitly limits automated evidence to CSS reflow, then received
   a fresh clean-clone replay and browser run.
5. Both `Meta +` and `Command +` were sent in the in-app browser. Neither changed
   `innerWidth`, `devicePixelRatio`, or `visualViewport.scale`; therefore they were
   not accepted as real browser zoom evidence and no screenshot was retained as a
   zoom result.
6. The first closure-tree `verify.sh` run failed one schema test because its fixture
   loaded the now-upgraded P002 Ticket and therefore already contained the fields
   the test intended to prove were required. The fixture now removes those fields
   before asserting rejection, making it independent of the live Ticket version.
   No production or provenance record failed validation.
7. Two first attempts to launch the final adversarial reviewer exhausted their
   startup-context budgets before reviewing the repository. They were discarded
   and are not counted as independent review evidence.
8. A fork-context adversarial reviewer then completed the review and withheld merge
   approval for two P2 findings: incomplete supersession of the impossible
   RUN-20260710-0005 commit chronology, and a validator that compared duplicated
   recorded hashes without recomputing file content. Both findings were accepted.
9. The content validator was repaired with Git-blob and retained-output hash
   recomputation plus negative tests. A fresh clean-clone replay was required after
   that code change; the earlier 44-test replay is not used as final evidence.
10. The first closure staging pass omitted `replay.log` because the repository's
    general `*.log` ignore rule applied. The omission was detected before commit;
    the evidence log was explicitly force-added and its manifest entry reverified.

No failed or reverted attempt is presented as passing evidence.
