# Literary parity execution preflight

- Checked at UTC: `2026-07-21T19:54:18Z`
- Status: `ready_for_execution`
- Passed checks: `27/27`
- Request SHA-256: `1e831372b4ecabad64cdc64f4a22455fe8b9916a26903fcf1320dd83bb2b7818`
- Frozen source commit: `31e09782ba07e6709cbdcca48bc9db22e6c49723`
- Frozen image: `ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa`

This is a results-blind readiness record. It contains no Delta distance,
direct R stylo result, MDS coordinate, cluster or authorship conclusion.

## Checks

| Check | Status | Detail |
|---|---|---|
| `dataset_identity` | `pass` | `"DATA-ENDTOEND-LIT-V1"` |
| `protocol_identity` | `pass` | `"PROTO-EVAL-DELTA-1.1"` |
| `frozen_commit` | `pass` | `"31e09782ba07e6709cbdcca48bc9db22e6c49723"` |
| `frozen_image` | `pass` | `"ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa"` |
| `release_freeze` | `pass` | `"frozen"` |
| `mfw_grid` | `pass` | `[100, 300, 500, 1000]` |
| `culling` | `pass` | `0` |
| `distance` | `pass` | `"classic_delta"` |
| `matrix_threshold` | `pass` | `1e-06` |
| `structural_threshold` | `pass` | `1e-12` |
| `exact_feature_order` | `pass` | `true` |
| `exact_label_order` | `pass` | `true` |
| `exact_tie_groups` | `pass` | `true` |
| `request_component_exact` | `pass` | `"28e9d3d83efa686b8b51b80eccd9b4f3439aeb56141e459abd97729c9c5b9184"` |
| `request_hash_bound` | `pass` | `"1e831372b4ecabad64cdc64f4a22455fe8b9916a26903fcf1320dd83bb2b7818"` |
| `request_frozen_contract` | `pass` | `{"canonical_request_sha256": "1e831372b4ecabad64cdc64f4a22455fe8b9916a26903fcf1320dd83bb2b7818", "distances": ["classic_delta", "classic_delta", "classic_delta", "classic_delta"], "document_count": 6, "mfw_grid": [100, 300, 500, 1000]}` |
| `request_document_count` | `pass` | `6` |
| `request_mfw_grid` | `pass` | `[100, 300, 500, 1000]` |
| `request_distance_grid` | `pass` | `["classic_delta", "classic_delta", "classic_delta", "classic_delta"]` |
| `results_blind_directories` | `pass` | `[]` |
| `local_execution_files_present` | `pass` | `{"scripts/build_literary_worker_request.py": "34430ee2e2b61528d804710ab645efe8ed24b318d8f00ce2774249abda3f8846", "scripts/compare_literary_parity.py": "e35bc9254d23a0f97b8f2e39ebaca73e8b1e4a35541d0a2830668c6ca38eda25", "scripts/direct_oracle_harness.R": "0f999f1d93c5cbce4f7e74f83df2914da4b41e7bfc90471fd85905b5dd96279b", "scripts/literary-parity-github-actions.yml": "f9f87470da3ac91a391becadc3478aa017f60251819004d8c03a92e9b5ab0032", "scripts/prepare_execution.py": "6f6957ca25557eb9f41942f54ce08d8c88ffee032b54e86836203048c62352cd"}` |
| `frozen_execution_files_bound` | `pass` | `{"containers/Dockerfile": "7e3812352e11f43f345f2a21886ab708e1737b910882efe096fde33cb181a996", "renv.lock": "bb792d224470650053412194edc35f3fd866673bd78d30ca756fcec3ad86ea1d", "scripts/oracles/p006-direct-stylo-v1.R": "61c08e25831a54df6bb25a3f96ce90908be181241bcc3165d09f1be8773e0630", "scripts/validate_p006_worker_parity.py": "53c4f71e8fc0d6fc405f5c54ea49571f43ab38e23d17fbebab3a8adac6a7432d", "scripts/workers/p006-stylo-worker-v1.R": "4cf9866a8a2c0fdf6011f711654f481e4b74326f518d1676fcf0a5b7eb2d2eb2", "src/delta_lemmata/data/stylo-worker-limits-v1.json": "6b7ccff1af42cdcc89ee5d62a2f6d179f3bd372ed1d2660d327f2cd6abf79702", "src/delta_lemmata/stylo_contracts.py": "1668d676d1dfff658778f7f0391b4457a8786b549b9c093efb43a54800ae5969", "uv.lock": "c6b6aa3d8e07cefff89f1072080fc7d9daa055692be8e02b10d224853986a385"}` |
| `workflow_commit_pin` | `pass` | `"31e09782ba07e6709cbdcca48bc9db22e6c49723"` |
| `workflow_image_pin` | `pass` | `"ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa"` |
| `workflow_component_pins` | `pass` | `{"fatal": "24ae13b5ee15a59e2f7924a480c4160907d13e900a8d879f1d81b0faab8f6548", "request": "28e9d3d83efa686b8b51b80eccd9b4f3439aeb56141e459abd97729c9c5b9184", "result": "053bf21e22c557bd2e9cc53b858b02603c19200680fe1cc2d885bd1b11d6987b"}` |
| `workflow_fatal_is_failure` | `pass` | `"fatal artifact rejected independently of process exit status"` |
| `repo_contains_frozen_commit` | `pass` | `"31e09782ba07e6709cbdcca48bc9db22e6c49723"` |
