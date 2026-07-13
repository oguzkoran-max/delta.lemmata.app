# P005 Final CI Validation

**Status:** Linux verification and canonical container passed for the final
implementation commit. Supply-chain generation passed, but GitHub artifact upload
is temporarily blocked by account storage recalculation. P005-AC-08 remains open.

**Date:** 2026-07-13

## Transparent Failure Sequence

1. Run `29219821591`, commit `c537a579f75774f4435e58f28a2e83ce4004574b`:
   the canonical Linux amd64 container passed. Linux test
   `test_second_control_failure_uses_emergency_kill_and_reap` exposed that the
   emergency path could return without collecting a killed leader when process
   enumeration failed a second time.
2. Run `29220096990`, commit `9597a5f1028354ec22ed661ce9a530b943afd380`:
   all 950 Linux tests passed, but the 100% coverage gate found a platform-dependent
   unexecuted error branch. The test clock was made deterministic.
3. Run `29220278021`, commit `2a17ec60ed62695e1e47383ad930330bef52f134`:
   950 Linux tests, 100% measured coverage, metadata, schemas, records, repository
   scan, locked R boundary, supply-chain generation, and the canonical Linux amd64
   container all passed. `actions/upload-artifact` alone failed because GitHub
   reported that the account artifact-storage quota had been reached.
4. The same final run was retried after deleting seven already-expired Windows
   build artifacts from `dtcf-sinav-programi-planlayici`. The verification,
   supply-chain generation, and existing container result remained green; upload
   was rejected again because GitHub states storage usage may take 6-12 hours to
   recalculate.
5. A third failed-job retry, verify job `86726382068`, was made about 20 minutes
   after deletion. All source and evidence-generation steps passed again; artifact
   upload returned the same quota-recalculation message.
6. A fourth failed-job retry at 2026-07-13 12:55 TRT, verify job `86786405954`,
   again passed environment restoration, all 950 tests with full measured coverage,
   record and repository gates, supply-chain generation, and the retained canonical
   container result. The upload action found all eight expected files but GitHub
   still reported the account storage quota as full. Further retries are deferred
   until 2026-07-13 18:55 TRT, the conservative end of the stated 6-12 hour
   recalculation window.

## Current Boundary

No code, test, SBOM-generation, dependency-audit, or container failure remains in
the final commit. The missing item is a downloadable retained CI artifact. The
upload step remains required and is not marked `continue-on-error`; therefore CI
correctly remains red and P005-AC-08 remains pending until GitHub accepts the
artifact and its downloaded checksums are verified.
