"""Application-process fixture killed by guardian integration tests."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from delta_lemmata.guardian_controller import GuardianController
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY
from delta_lemmata.job_store import SQLiteJobStore
from delta_lemmata.recovery_receipt import RecoveryReceiptStore
from delta_lemmata.session_identity import JobId

SIGNING_SECRET = b"guardian-app-loss-secret-v1-32bytes"
OWNER_SECRET = b"guardian-job-owner-secret-v1-32bytes"


def main() -> int:
    if len(sys.argv) != 11:
        return 2
    ready_file = Path(sys.argv[1])
    worker = Path(sys.argv[2])
    workspace_root = Path(sys.argv[3])
    owner_component = sys.argv[4]
    job_component = sys.argv[5]
    receipt_root = Path(sys.argv[6])
    job_id = JobId.from_urlsafe(sys.argv[7])
    mode = sys.argv[8]
    database_file = Path(sys.argv[9])
    execution_reference = sys.argv[10]
    controller = GuardianController(
        argv=(sys.executable, str(worker), mode),
        cwd=ready_file.parent,
        limits=DEFAULT_JOB_POLICY.worker_limits,
        job_id=job_id,
        execution_reference=execution_reference,
        store=SQLiteJobStore(database_file, owner_secret=OWNER_SECRET),
        workspace_root=workspace_root,
        owner_component=owner_component,
        job_component=job_component,
        receipt_store=RecoveryReceiptStore(
            receipt_root,
            signing_secret=SIGNING_SECRET,
        ),
    )
    controller.start()
    ready_file.write_text(str(controller.process_group_id), encoding="ascii")
    os.chmod(ready_file, 0o600)
    while True:
        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())
