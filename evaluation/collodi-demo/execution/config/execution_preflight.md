# Collodi demo execution preflight

- Checked at UTC: `2026-08-02T21:06:33Z`
- Status: `ready_for_execution`
- Passed checks: `25/25`
- Request SHA-256: `0eb1c53ca5e1f930cd7a331cf13b6b090cf68083b8a16a0bb846c496160fe5f0`
- Frozen source commit: `31e09782ba07e6709cbdcca48bc9db22e6c49723`
- Frozen image: `ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa`

This is a results-blind readiness record. It contains no Delta distance,
MDS coordinate, cluster, authorship claim or diachronic inference.

## Checks

| Check | Status | Detail |
|---|---|---|
| `dataset_identity` | `pass` | `"DATA-COLLODI-DEMO-V1"` |
| `protocol_identity` | `pass` | `"PROTO-EVAL-DELTA-1.1"` |
| `results_blind_state` | `pass` | `"results_blind_prepared"` |
| `document_count` | `pass` | `3` |
| `mfw_grid` | `pass` | `[100, 300, 500, 1000]` |
| `culling` | `pass` | `0` |
| `distance` | `pass` | `"classic_delta"` |
| `display_mfw` | `pass` | `500` |
| `claim_restrictions` | `pass` | `["ageing_claim", "authorship_attribution_claim", "causal_Pinocchio_effect_claim", "formal_periodisation_claim", "population_inference"]` |
| `upstream_lock_manifest` | `pass` | `{"dataset_lock_id": "DATA-COLLODI-DEMO-V1", "manifest_sha256": "f740e4c57c11d376346d4c7a8cc5d23fbea5c28544167de3ee2f0d496f7f4292", "outcomes_sha256_at_lock": "135d2951d8df399d9f7e659209d3c876b1ca2cad5f4df8417f95b73e3321dd96", "shared_distinct_10grams": 1, "validated_documents": 3, "validation_status": "PASS"}` |
| `outcomes_state_at_lock` | `pass` | `"135d2951d8df399d9f7e659209d3c876b1ca2cad5f4df8417f95b73e3321dd96"` |
| `frozen_commit` | `pass` | `"31e09782ba07e6709cbdcca48bc9db22e6c49723"` |
| `frozen_image` | `pass` | `"ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa"` |
| `request_component_exact` | `pass` | `"28e9d3d83efa686b8b51b80eccd9b4f3439aeb56141e459abd97729c9c5b9184"` |
| `request_hash_bound` | `pass` | `"0eb1c53ca5e1f930cd7a331cf13b6b090cf68083b8a16a0bb846c496160fe5f0"` |
| `candidate_feature_range` | `pass` | `13495` |
| `results_blind_files` | `pass` | `[]` |
| `frozen_source_file_hashes` | `pass` | `{"containers/Dockerfile": "7e3812352e11f43f345f2a21886ab708e1737b910882efe096fde33cb181a996", "renv.lock": "bb792d224470650053412194edc35f3fd866673bd78d30ca756fcec3ad86ea1d", "scripts/oracles/p006-direct-stylo-v1.R": "61c08e25831a54df6bb25a3f96ce90908be181241bcc3165d09f1be8773e0630", "scripts/validate_p006_worker_parity.py": "53c4f71e8fc0d6fc405f5c54ea49571f43ab38e23d17fbebab3a8adac6a7432d", "scripts/workers/p006-stylo-worker-v1.R": "4cf9866a8a2c0fdf6011f711654f481e4b74326f518d1676fcf0a5b7eb2d2eb2", "src/delta_lemmata/data/stylo-worker-limits-v1.json": "6b7ccff1af42cdcc89ee5d62a2f6d179f3bd372ed1d2660d327f2cd6abf79702", "src/delta_lemmata/stylo_contracts.py": "1668d676d1dfff658778f7f0391b4457a8786b549b9c093efb43a54800ae5969", "uv.lock": "c6b6aa3d8e07cefff89f1072080fc7d9daa055692be8e02b10d224853986a385"}` |
| `accepted_comparator_unchanged` | `pass` | `"70e3c9ef9801eb4af52854aae9c4bd4f8b67de20ed7e3fc768e5ecaebd566836"` |
| `workflow_security_and_identity_pins` | `pass` | `"commit+image+components+network-none+read-only+cap-drop"` |
| `deterministic_input_tree` | `pass` | `{"file_count": 15, "tree_sha256": "7bb4cfd15038d39c070c0b4e3882f2ca386964c6a352286610ab625d1252f001"}` |
| `frozen_request_contract` | `pass` | `"0eb1c53ca5e1f930cd7a331cf13b6b090cf68083b8a16a0bb846c496160fe5f0"` |
| `request_document_count` | `pass` | `3` |
| `request_mfw_grid` | `pass` | `[100, 300, 500, 1000]` |
| `request_distance_grid` | `pass` | `["classic_delta", "classic_delta", "classic_delta", "classic_delta"]` |
