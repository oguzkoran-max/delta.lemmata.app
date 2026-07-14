#!/usr/bin/env python3
"""Validate the real P006 R-to-SQLite-to-guardian handoff on canonical Linux."""

from __future__ import annotations

import hashlib
import platform
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NoReturn

from delta_lemmata.clock import FakeClock
from delta_lemmata.job_models import CleanupState, ExecutionState, TerminalOutcome
from delta_lemmata.job_store import SQLiteJobStore
from delta_lemmata.job_workspace import WorkspaceArea, WorkspaceManager
from delta_lemmata.recovery_receipt import RecoveryReceiptStore
from delta_lemmata.session_identity import JobId, SessionCapability, workspace_component
from delta_lemmata.stylo_contracts import parse_worker_input
from delta_lemmata.stylo_job_runner import StyloJobRunner
from delta_lemmata.stylo_worker import RESULT_COMPONENT

ROOT = Path(__file__).resolve().parents[1]
REQUEST_PATH = (
    ROOT / "tests" / "fixtures" / "stylo" / "p006-whole-text-v2" / "normalization-base.input.json"
)
OWNER_SECRET = b"p006-handoff-owner-secret-v1-32bytes"
RECEIPT_SECRET = b"p006-handoff-receipt-secret-v1-32b"


def _fail(code: str) -> NoReturn:
    raise ValueError(code) from None


def _operation(number: int) -> str:
    return "op_" + f"{number:064x}"


def validate_scientific_handoff() -> None:
    if platform.system() != "Linux":
        _fail("P006_HANDOFF_CANONICAL_LINUX_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="delta-p006-handoff-") as temporary:
        root = Path(temporary)
        database_root = root / "database"
        workspace_root = root / "workspaces"
        receipt_root = root / "receipts"
        for directory in (database_root, workspace_root, receipt_root):
            directory.mkdir(mode=0o700)

        now = datetime.now(UTC)
        job_id = JobId.generate(lambda size: b"j" * size)
        capability = SessionCapability.generate(lambda size: b"c" * size)
        store = SQLiteJobStore(
            database_root / "control.sqlite3",
            owner_secret=OWNER_SECRET,
            job_id_factory=lambda: job_id,
        )
        staged = store.stage_job(capability=capability, at_utc=now)
        store.enqueue_job(
            job_id=staged.job_id,
            capability=capability,
            at_utc=now + timedelta(microseconds=1),
            expected_version=staged.version,
            operation_id=_operation(1),
        )
        running = store.claim_next(
            at_utc=now + timedelta(microseconds=2),
            operation_id=_operation(2),
        )
        if running is None:
            _fail("P006_HANDOFF_CLAIM_FAILED")
        workspaces = WorkspaceManager(workspace_root)
        layout = workspaces.create(running.owner_digest, workspace_component(job_id))
        receipts = RecoveryReceiptStore(receipt_root, signing_secret=RECEIPT_SECRET)
        request = parse_worker_input(REQUEST_PATH.read_bytes())
        operation_numbers = iter((3, 4, 5))
        runner = StyloJobRunner(
            store=store,
            workspaces=workspaces,
            receipts=receipts,
            clock=FakeClock(now + timedelta(seconds=1)),
            operation_id_factory=lambda: _operation(next(operation_numbers)),
        )

        saved = runner.run(job=running, layout=layout, request=request)
        receipt = saved.scientific_result
        if (
            saved.execution.state is not ExecutionState.TERMINAL
            or saved.outcome is None
            or saved.outcome.kind is not TerminalOutcome.SUCCEEDED
            or saved.artifacts.result.state is not CleanupState.PRESENT
            or not saved.scientific_result_confirmed
            or receipt is None
        ):
            _fail("P006_HANDOFF_TERMINAL_COMMIT_INVALID")
        retained = workspaces.read_file(
            layout,
            WorkspaceArea.RESULT,
            RESULT_COMPONENT,
            maximum_bytes=receipt.byte_size,
        )
        if (
            retained is None
            or len(retained) != receipt.byte_size
            or hashlib.sha256(retained).hexdigest() != receipt.sha256
        ):
            _fail("P006_HANDOFF_RETAINED_RESULT_INVALID")
        if not any(
            operation.action.startswith("scientific:guardian:confirmed:")
            for operation in saved.operations
        ):
            _fail("P006_HANDOFF_SQLITE_COMMIT_INVALID")
        disposition = receipts.read(job_id, _operation(2))
        if (
            disposition is None
            or disposition.outcome != "accepted"
            or disposition.terminal_version != saved.version - 1
            or disposition.terminal_outcome is not TerminalOutcome.SUCCEEDED
            or disposition.artifact_sha256 != receipt.sha256
            or disposition.artifact_byte_size != receipt.byte_size
        ):
            _fail("P006_HANDOFF_GUARDIAN_DISPOSITION_INVALID")


def main() -> int:
    validate_scientific_handoff()
    print("p006-scientific-handoff-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
