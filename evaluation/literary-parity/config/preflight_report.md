# Frozen Literary Parity Preflight

- Checked at (UTC): `2026-07-20T10:45:08Z`
- Freeze: `FREEZE-LIT-PARITY-20260720-01`
- Commit: `31e09782ba07e6709cbdcca48bc9db22e6c49723`
- Image: `ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa`
- Configuration SHA-256: `79598bbd19dc4b88d1d1076730f8c10b1c1259b608528e1855c1e5cd7ccc84b1`
- Status: `blocked_exact_reference_execution_path`
- Analysis started: `false`
- Stylometric result created: `false`

## Checks

| Check | Status | Detail |
|---|---|---|
| `dataset_identity` | `pass` | DATA-ENDTOEND-LIT-V1 |
| `protocol_identity` | `pass` | PROTO-EVAL-DELTA-1.1 |
| `mfw_grid` | `pass` | [100, 300, 500, 1000] |
| `configuration_state` | `pass` | preflight_blocked_exact_reference_execution_path |
| `release_freeze_state` | `pass` | frozen |
| `release_commit_match` | `pass` | 31e09782ba07e6709cbdcca48bc9db22e6c49723 |
| `release_image_match` | `pass` | ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa |
| `release_ci_success` | `pass` | 29696014941 |
| `release_publication_success` | `pass` | 29696211566 |
| `no_release_result` | `pass` | analysis_result_created=false |
| `four_preregistered_runs` | `pass` | rows=4 |
| `run_mfw_grid` | `pass` | [100, 300, 500, 1000] |
| `run_config_hash` | `pass` | 79598bbd19dc4b88d1d1076730f8c10b1c1259b608528e1855c1e5cd7ccc84b1 |
| `run_release_commit` | `pass` | 31e09782ba07e6709cbdcca48bc9db22e6c49723 |
| `run_release_image` | `pass` | ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa |
| `run_status` | `pass` | preflight_blocked_exact_reference_execution_path |
| `result_hashes_blank` | `pass` | four blank result_sha256 fields |
| `outcomes_empty` | `pass` | rows=0 |
| `result_folders_empty` | `pass` | [] |
| `local_r_version` | `pass` | 4.5.2 |
| `stylo_version` | `pass` | 0.7.71 |
| `stylo_delta_kernel_smoke` | `pass` | 0 |

## Interpretation

The frozen corpus, configuration, release identity, run-register rows, and exact `stylo 0.7.71` numerical kernel pass results-blind checks. Actual parity execution remains blocked until an auditable route can invoke the direct R reference and the frozen Delta release. No result or parity claim is created by this report.

## Limitations

- The normal macOS stylo namespace was not attached because its imported GUI stack requires XQuartz; the exact 0.7.71 lazy-load object database was used only for this numerical-kernel smoke test.
- Direct readback from the live host remains unavailable because SSH timed out during banner exchange before authentication.
- No local Docker, Podman, Colima, nerdctl, or OrbStack runtime was available for executing the frozen OCI image.
- This preflight creates no stylometric result and does not test Delta-versus-R parity.
