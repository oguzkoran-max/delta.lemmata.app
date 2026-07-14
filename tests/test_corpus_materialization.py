from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from delta_lemmata.clock import FakeClock
from delta_lemmata.corpus_materialization import (
    CorpusMaterializationError,
    CorpusMaterializationErrorCode,
    CorpusMaterializationService,
)
from delta_lemmata.ingestion import (
    IntakeReceipt,
    IntakeRole,
    ValidatedCorpusPayload,
)
from delta_lemmata.job_service import (
    JobAdmission,
    JobService,
    JobServiceError,
    JobServiceErrorCode,
)
from delta_lemmata.job_staging import MaterializationReceipt
from delta_lemmata.job_store import SQLiteJobStore
from delta_lemmata.job_workspace import WorkspaceManager
from delta_lemmata.session_identity import JobId, SessionCapability

NOW = datetime(2026, 7, 14, 21, 0, tzinfo=UTC)
SECRET = b"p007-materialization-owner-secret-32bytes"


class JobIds:
    def __init__(self) -> None:
        self.value = 20

    def __call__(self) -> JobId:
        value = self.value
        self.value += 1
        return JobId.generate(lambda size: bytes([value]) * size)


class LeaseIds:
    def __init__(self) -> None:
        self.value = 0

    def __call__(self) -> str:
        self.value += 1
        return f"{self.value:064x}"


def _source(index: int, content: bytes) -> ValidatedCorpusPayload:
    digest = hashlib.sha256(content).hexdigest()
    receipt = IntakeReceipt(
        asset_id="asset_" + f"{index:032x}",
        role=IntakeRole.CORPUS_TEXT,
        display_label=f"private-{index}.txt",
        storage_name="asset_" + f"{index:032x}" + ".txt",
        byte_size=len(content),
        expanded_bytes=len(content),
        sha256=digest,
        line_count=1,
        token_count=3,
        limit_profile="ingestion-limits-v1",
    )
    return ValidatedCorpusPayload(receipt=receipt, content=content)


def _environment(tmp_path: Path, *, lease_ids=None, capability_factory=None):
    database = tmp_path / "database"
    workspaces_root = tmp_path / "workspaces"
    database.mkdir(mode=0o700, parents=True)
    workspaces_root.mkdir(mode=0o700, parents=True)
    clock = FakeClock(NOW)
    store = SQLiteJobStore(
        database / "control.sqlite3",
        owner_secret=SECRET,
        job_id_factory=JobIds(),
    )
    workspaces = WorkspaceManager(workspaces_root)
    jobs = JobService(store=store, workspaces=workspaces, clock=clock)
    capabilities = iter(
        SessionCapability.generate(lambda size, value=value: bytes([value]) * size)
        for value in range(1, 10)
    )
    make_capability = capability_factory or (lambda: next(capabilities))
    service = CorpusMaterializationService(
        jobs=jobs,
        workspaces=workspaces,
        clock=clock,
        lease_id_factory=lease_ids or LeaseIds(),
        capability_factory=make_capability,
    )
    return service, workspaces, clock


def _expect_error(action, code: CorpusMaterializationErrorCode) -> None:
    with pytest.raises(CorpusMaterializationError) as captured:
        action()
    assert captured.value.code is code
    assert str(captured.value) == code.value
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None


def test_materialization_returns_only_a_payload_free_public_receipt(tmp_path: Path) -> None:
    service, workspaces, _clock = _environment(tmp_path)
    sources = (
        _source(1, b"first private corpus"),
        _source(2, b"second private corpus"),
    )

    receipt = service.materialize(owner_key="streamlit-session-one", payloads=sources)

    assert receipt.source_count == 2
    assert receipt.byte_count == sum(len(item.content) for item in sources)
    assert receipt.expires_at_utc == NOW + timedelta(hours=1)
    assert "private corpus" not in repr(receipt)
    assert "capability" not in repr(receipt).casefold()
    assert not hasattr(receipt, "file_component")
    assert len(workspaces.list_layouts()) == 1
    assert len(tuple(workspaces.list_layouts()[0].input.iterdir())) == 2


def test_visit_reauthorizes_owner_and_rechecks_every_staged_digest(tmp_path: Path) -> None:
    service, workspaces, _clock = _environment(tmp_path)
    sources = (
        _source(1, b"first private corpus"),
        _source(2, b"second private corpus"),
    )
    receipt = service.materialize(owner_key="owner-a", payloads=sources)

    _expect_error(
        lambda: service.visit(
            owner_key="owner-b",
            receipt=receipt,
            visitor=lambda _payloads: None,
        ),
        CorpusMaterializationErrorCode.NOT_AVAILABLE,
    )
    observed = service.visit(
        owner_key="owner-a",
        receipt=receipt,
        visitor=lambda payloads: tuple(item.content for item in payloads),
    )
    assert observed == tuple(item.content for item in sources)
    assert len(workspaces.list_layouts()) == 1

    cleanup = service.cleanup(owner_key="owner-a", receipt=receipt)
    assert cleanup.file_count == 2
    assert cleanup.byte_count == receipt.byte_count
    assert workspaces.list_layouts() == ()


def test_integrity_failure_and_visitor_failure_remove_private_workspace(tmp_path: Path) -> None:
    service, workspaces, _clock = _environment(tmp_path)
    source = _source(1, b"private canary corpus")
    receipt = service.materialize(owner_key="owner-a", payloads=(source,))
    staged_file = next(workspaces.list_layouts()[0].input.iterdir())
    staged_file.write_bytes(b"mutated canary corpus")

    _expect_error(
        lambda: service.visit(
            owner_key="owner-a",
            receipt=receipt,
            visitor=lambda _payloads: None,
        ),
        CorpusMaterializationErrorCode.INTEGRITY,
    )
    assert workspaces.list_layouts() == ()

    second = service.materialize(owner_key="owner-a", payloads=(source,))

    def fail(_payloads) -> None:
        raise RuntimeError("private canary corpus")

    _expect_error(
        lambda: service.visit(owner_key="owner-a", receipt=second, visitor=fail),
        CorpusMaterializationErrorCode.PREPARATION_FAILED,
    )
    assert workspaces.list_layouts() == ()


def test_expiry_invalid_receipts_and_duplicate_lease_ids_fail_closed(tmp_path: Path) -> None:
    service, workspaces, clock = _environment(tmp_path)
    source = _source(1, b"private canary corpus")
    receipt = service.materialize(owner_key="owner-a", payloads=(source,))
    clock.advance(timedelta(hours=1))
    _expect_error(
        lambda: service.visit(
            owner_key="owner-a",
            receipt=receipt,
            visitor=lambda _payloads: None,
        ),
        CorpusMaterializationErrorCode.EXPIRED,
    )
    assert workspaces.list_layouts() == ()

    _expect_error(
        lambda: service.materialize(owner_key="", payloads=(source,)),
        CorpusMaterializationErrorCode.INVALID_REQUEST,
    )
    _expect_error(
        lambda: service.materialize(owner_key="owner-a", payloads=()),
        CorpusMaterializationErrorCode.INVALID_REQUEST,
    )
    _expect_error(
        lambda: service.visit(
            owner_key="owner-a",
            receipt=receipt,
            visitor=None,  # type: ignore[arg-type]
        ),
        CorpusMaterializationErrorCode.INVALID_REQUEST,
    )

    def constant_ids() -> str:
        return "f" * 64

    duplicate_service, duplicate_workspaces, _ = _environment(
        tmp_path / "duplicates",
        lease_ids=constant_ids,
    )
    first = duplicate_service.materialize(owner_key="owner-a", payloads=(source,))
    _expect_error(
        lambda: duplicate_service.materialize(owner_key="owner-b", payloads=(source,)),
        CorpusMaterializationErrorCode.INVALID_IDENTIFIER,
    )
    assert len(duplicate_workspaces.list_layouts()) == 1
    duplicate_service.cleanup(owner_key="owner-a", receipt=first)


def test_configuration_owner_identifier_and_unexpected_failures_are_content_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, workspaces, clock = _environment(tmp_path)
    source = _source(1, b"private defensive corpus")

    _expect_error(
        lambda: CorpusMaterializationService(
            jobs=object(),  # type: ignore[arg-type]
            workspaces=workspaces,
            clock=clock,
            lease_id_factory=LeaseIds(),
        ),
        CorpusMaterializationErrorCode.INVALID_CONFIGURATION,
    )
    _expect_error(
        lambda: service.materialize(owner_key="\ud800", payloads=(source,)),
        CorpusMaterializationErrorCode.INVALID_REQUEST,
    )

    def broken_identifier() -> str:
        raise RuntimeError("private defensive corpus")

    broken_service, _broken_workspaces, _ = _environment(
        tmp_path / "broken-identifier",
        lease_ids=broken_identifier,
    )
    _expect_error(
        lambda: broken_service.materialize(owner_key="owner-a", payloads=(source,)),
        CorpusMaterializationErrorCode.INVALID_IDENTIFIER,
    )
    invalid_service, _invalid_workspaces, _ = _environment(
        tmp_path / "invalid-identifier",
        lease_ids=lambda: "not-a-lease-id",
    )
    _expect_error(
        lambda: invalid_service.materialize(owner_key="owner-a", payloads=(source,)),
        CorpusMaterializationErrorCode.INVALID_IDENTIFIER,
    )

    def unexpected_failure() -> str:
        raise RuntimeError("private defensive corpus")

    monkeypatch.setattr(service, "_reserve_lease_id", unexpected_failure)
    _expect_error(
        lambda: service.materialize(owner_key="owner-a", payloads=(source,)),
        CorpusMaterializationErrorCode.OPERATION_FAILED,
    )
    assert workspaces.list_layouts() == ()


def test_capability_and_job_admission_failures_leave_no_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(1, b"private admission corpus")
    invalid_capability, invalid_workspaces, _ = _environment(
        tmp_path / "invalid-capability",
        capability_factory=lambda: object(),
    )
    _expect_error(
        lambda: invalid_capability.materialize(owner_key="owner-a", payloads=(source,)),
        CorpusMaterializationErrorCode.ADMISSION_REJECTED,
    )
    assert invalid_workspaces.list_layouts() == ()

    def fail_capability() -> SessionCapability:
        raise RuntimeError("private admission corpus")

    failed_capability, failed_workspaces, _ = _environment(
        tmp_path / "failed-capability",
        capability_factory=fail_capability,
    )
    _expect_error(
        lambda: failed_capability.materialize(owner_key="owner-a", payloads=(source,)),
        CorpusMaterializationErrorCode.ADMISSION_REJECTED,
    )
    assert failed_workspaces.list_layouts() == ()

    service, workspaces, _ = _environment(tmp_path / "failed-admission")

    def fail_admission(**_kwargs) -> JobAdmission:
        raise RuntimeError("private admission corpus")

    monkeypatch.setattr(service._jobs, "admit", fail_admission)
    _expect_error(
        lambda: service.materialize(owner_key="owner-a", payloads=(source,)),
        CorpusMaterializationErrorCode.ADMISSION_REJECTED,
    )
    assert workspaces.list_layouts() == ()


@pytest.mark.parametrize("mutation", ["deadline", "asset-count", "asset-metadata"])
def test_admission_integrity_failures_roll_back_private_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    service, workspaces, _ = _environment(tmp_path / mutation)
    source = _source(1, b"private integrity corpus")
    original_admit = service._jobs.admit

    def altered_admission(**kwargs) -> JobAdmission:
        admission = original_admit(**kwargs)
        if mutation == "deadline":
            execution = admission.job.execution.model_copy(update={"deadline_at_utc": None})
            job = admission.job.model_copy(update={"execution": execution})
            return replace(admission, job=job)
        if mutation == "asset-count":
            materialization = MaterializationReceipt(assets=(), file_count=0, byte_count=0)
            return replace(admission, materialization=materialization)
        first = admission.materialization.assets[0]
        digest = "e" * 64 if first.sha256 == "f" * 64 else "f" * 64
        materialization = replace(
            admission.materialization,
            assets=(replace(first, sha256=digest),),
        )
        return replace(admission, materialization=materialization)

    monkeypatch.setattr(service._jobs, "admit", altered_admission)
    _expect_error(
        lambda: service.materialize(owner_key="owner-a", payloads=(source,)),
        CorpusMaterializationErrorCode.INTEGRITY,
    )
    assert workspaces.list_layouts() == ()


def test_failed_admission_rollback_reports_cleanup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, workspaces, _ = _environment(tmp_path)
    source = _source(1, b"private rollback corpus")
    original_admit = service._jobs.admit
    original_cleanup = service._jobs.cleanup
    admitted: list[tuple[JobAdmission, SessionCapability]] = []

    def altered_admission(**kwargs) -> JobAdmission:
        admission = original_admit(**kwargs)
        admitted.append((admission, kwargs["capability"]))
        materialization = MaterializationReceipt(assets=(), file_count=0, byte_count=0)
        return replace(admission, materialization=materialization)

    def fail_cleanup(**_kwargs):
        raise RuntimeError("private rollback corpus")

    monkeypatch.setattr(service._jobs, "admit", altered_admission)
    monkeypatch.setattr(service._jobs, "cleanup", fail_cleanup)
    _expect_error(
        lambda: service.materialize(owner_key="owner-a", payloads=(source,)),
        CorpusMaterializationErrorCode.CLEANUP_FAILED,
    )
    assert len(workspaces.list_layouts()) == 1

    admission, capability = admitted[0]
    original_cleanup(job_id=admission.job.job_id, capability=capability)
    assert workspaces.list_layouts() == ()


def test_invalid_clock_cleans_materialization_and_reports_configuration_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, workspaces, _ = _environment(tmp_path)
    source = _source(1, b"private clock corpus")
    receipt = service.materialize(owner_key="owner-a", payloads=(source,))

    class BrokenClock:
        def now(self) -> datetime:
            raise RuntimeError("private clock corpus")

    monkeypatch.setattr(service, "_clock", BrokenClock())
    _expect_error(
        lambda: service.visit(
            owner_key="owner-a",
            receipt=receipt,
            visitor=lambda _payloads: None,
        ),
        CorpusMaterializationErrorCode.INVALID_CONFIGURATION,
    )
    assert workspaces.list_layouts() == ()


def test_cleanup_failure_retains_authority_for_a_bounded_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, workspaces, _ = _environment(tmp_path)
    source = _source(1, b"private cleanup corpus")
    receipt = service.materialize(owner_key="owner-a", payloads=(source,))
    original_cleanup = service._jobs.cleanup

    def fail_cleanup(**_kwargs):
        raise RuntimeError("private cleanup corpus")

    monkeypatch.setattr(service._jobs, "cleanup", fail_cleanup)
    _expect_error(
        lambda: service.cleanup(owner_key="owner-a", receipt=receipt),
        CorpusMaterializationErrorCode.CLEANUP_FAILED,
    )
    assert len(workspaces.list_layouts()) == 1

    monkeypatch.setattr(service._jobs, "cleanup", original_cleanup)
    report = service.cleanup(owner_key="owner-a", receipt=receipt)
    assert report.verified_absent is True
    assert workspaces.list_layouts() == ()


def test_internal_race_guards_are_idempotent_and_cleanup_rejects_wrong_type(
    tmp_path: Path,
) -> None:
    service, workspaces, _ = _environment(tmp_path)
    source = _source(1, b"private race corpus")
    receipt = service.materialize(owner_key="owner-a", payloads=(source,))

    _expect_error(
        lambda: service.cleanup(
            owner_key="owner-a",
            receipt=object(),  # type: ignore[arg-type]
        ),
        CorpusMaterializationErrorCode.INVALID_REQUEST,
    )

    state = service._leases[receipt.lease_id]
    service._remove(state)
    service._remove(state)
    service._finish_visit(state)
    report = service._jobs.cleanup(job_id=receipt.job_id, capability=state.capability)
    assert report.verified_absent is True
    assert workspaces.list_layouts() == ()


def test_one_capability_is_reused_for_each_server_session(tmp_path: Path) -> None:
    generated: list[SessionCapability] = []

    def make_capability() -> SessionCapability:
        capability = SessionCapability.generate(lambda size: bytes([len(generated) + 1]) * size)
        generated.append(capability)
        return capability

    service, _workspaces, _clock = _environment(
        tmp_path,
        capability_factory=make_capability,
    )
    source = _source(1, b"private session corpus")

    first = service.materialize(owner_key="owner-a", payloads=(source,))
    first_state = service._leases[first.lease_id]
    owner_reference = first_state.owner_reference
    first_claim = service._capability_for(owner_reference)
    second_claim = service._capability_for(owner_reference)
    assert first_claim is first_state.capability
    assert second_claim is first_claim
    service._evict_unused_capability(owner_reference)
    service._release_capability_claim(owner_reference)
    service._release_capability_claim(owner_reference)
    _expect_error(
        lambda: service.materialize(owner_key="owner-a", payloads=(source,)),
        CorpusMaterializationErrorCode.ADMISSION_REJECTED,
    )
    assert len(generated) == 1
    service.cleanup(owner_key="owner-a", receipt=first)
    assert service._capabilities == {}
    assert service._capability_claims == {}
    second = service.materialize(owner_key="owner-a", payloads=(source,))
    service.cleanup(owner_key="owner-a", receipt=second)
    third = service.materialize(owner_key="owner-b", payloads=(source,))
    service.cleanup(owner_key="owner-b", receipt=third)

    assert len(generated) == 3
    assert service._capabilities == {}
    assert service._capability_claims == {}


def test_workspace_visit_and_ready_authority_enqueue_exactly_once(tmp_path: Path) -> None:
    service, workspaces, clock = _environment(tmp_path)
    source = _source(1, b"private ready corpus")
    receipt = service.materialize(owner_key="owner-a", payloads=(source,))

    observed = service._visit_workspace(
        owner_key="owner-a",
        receipt=receipt,
        visitor=lambda payloads, layout: (payloads[0].content, layout.root),
    )
    assert observed == (source.content, workspaces.list_layouts()[0].root)

    ready_hmac = "a" * 64
    service.bind_ready(
        owner_key="owner-a",
        receipt=receipt,
        ready_receipt_hmac=ready_hmac,
        expires_at_utc=receipt.expires_at_utc,
    )
    service.bind_ready(
        owner_key="owner-a",
        receipt=receipt,
        ready_receipt_hmac=ready_hmac,
        expires_at_utc=receipt.expires_at_utc,
    )
    assert service.status(owner_key="owner-a", receipt=receipt).state_id == "staged"
    visited = False

    def forbidden_visit(_payloads, _layout) -> None:
        nonlocal visited
        visited = True

    _expect_error(
        lambda: service._visit_workspace(
            owner_key="owner-a",
            receipt=receipt,
            visitor=forbidden_visit,
            ready_receipt_hmac="f" * 64,
        ),
        CorpusMaterializationErrorCode.READY_REJECTED,
    )
    assert visited is False

    queued = service.consume_ready(
        owner_key="owner-a",
        receipt=receipt,
        ready_receipt_hmac=ready_hmac,
        operation_id="op_" + "b" * 64,
    )
    assert queued.state_id == "queued"
    assert service.status(owner_key="owner-a", receipt=receipt).state_id == "queued"
    clock.advance(timedelta(hours=1))
    assert service.status(owner_key="owner-a", receipt=receipt).state_id == "queued"
    _expect_error(
        lambda: service.visit(
            owner_key="owner-a",
            receipt=receipt,
            visitor=lambda _payloads: None,
        ),
        CorpusMaterializationErrorCode.NOT_AVAILABLE,
    )
    _expect_error(
        lambda: service._visit_workspace(
            owner_key="owner-a",
            receipt=receipt,
            visitor=lambda _payloads, _layout: None,
            ready_receipt_hmac=ready_hmac,
        ),
        CorpusMaterializationErrorCode.READY_REUSED,
    )
    _expect_error(
        lambda: service.consume_ready(
            owner_key="owner-a",
            receipt=receipt,
            ready_receipt_hmac=ready_hmac,
            operation_id="op_" + "b" * 64,
        ),
        CorpusMaterializationErrorCode.READY_REUSED,
    )


def test_ready_authority_rejects_mismatch_and_cleans_at_exact_expiry(tmp_path: Path) -> None:
    service, workspaces, clock = _environment(tmp_path)
    source = _source(1, b"private expiring corpus")
    receipt = service.materialize(owner_key="owner-a", payloads=(source,))
    ready_hmac = "c" * 64
    service.bind_ready(
        owner_key="owner-a",
        receipt=receipt,
        ready_receipt_hmac=ready_hmac,
        expires_at_utc=receipt.expires_at_utc,
    )
    _expect_error(
        lambda: service.consume_ready(
            owner_key="owner-a",
            receipt=receipt,
            ready_receipt_hmac="d" * 64,
            operation_id="op_" + "e" * 64,
        ),
        CorpusMaterializationErrorCode.READY_REJECTED,
    )
    clock.advance(timedelta(hours=1))
    _expect_error(
        lambda: service.consume_ready(
            owner_key="owner-a",
            receipt=receipt,
            ready_receipt_hmac=ready_hmac,
            operation_id="op_" + "e" * 64,
        ),
        CorpusMaterializationErrorCode.EXPIRED,
    )
    assert workspaces.list_layouts() == ()

    status_service, status_workspaces, status_clock = _environment(tmp_path / "status-expiry")
    status_receipt = status_service.materialize(owner_key="owner-a", payloads=(source,))
    status_clock.advance(timedelta(hours=1))
    _expect_error(
        lambda: status_service.status(owner_key="owner-a", receipt=status_receipt),
        CorpusMaterializationErrorCode.EXPIRED,
    )
    assert status_workspaces.list_layouts() == ()


def test_ready_boundary_validates_inputs_bindings_and_store_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(1, b"private ready boundary corpus")
    service, workspaces, _clock = _environment(tmp_path / "bindings")
    receipt = service.materialize(owner_key="owner-a", payloads=(source,))
    ready_hmac = "a" * 64

    _expect_error(
        lambda: service._visit_workspace(
            owner_key="owner-a",
            receipt=object(),  # type: ignore[arg-type]
            visitor=lambda _payloads, _layout: None,
        ),
        CorpusMaterializationErrorCode.INVALID_REQUEST,
    )
    _expect_error(
        lambda: service._visit_workspace(
            owner_key="owner-a",
            receipt=receipt,
            visitor=lambda _payloads, _layout: None,
            ready_receipt_hmac="bad",
        ),
        CorpusMaterializationErrorCode.INVALID_REQUEST,
    )
    _expect_error(
        lambda: service.bind_ready(
            owner_key="owner-a",
            receipt=receipt,
            ready_receipt_hmac="bad",
            expires_at_utc=receipt.expires_at_utc,
        ),
        CorpusMaterializationErrorCode.INVALID_REQUEST,
    )
    _expect_error(
        lambda: service.consume_ready(
            owner_key="owner-a",
            receipt=receipt,
            ready_receipt_hmac=ready_hmac,
            operation_id=object(),  # type: ignore[arg-type]
        ),
        CorpusMaterializationErrorCode.INVALID_REQUEST,
    )
    _expect_error(
        lambda: service.status(
            owner_key="owner-a",
            receipt=object(),  # type: ignore[arg-type]
        ),
        CorpusMaterializationErrorCode.INVALID_REQUEST,
    )

    service.bind_ready(
        owner_key="owner-a",
        receipt=receipt,
        ready_receipt_hmac=ready_hmac,
        expires_at_utc=receipt.expires_at_utc,
    )
    _expect_error(
        lambda: service.bind_ready(
            owner_key="owner-a",
            receipt=receipt,
            ready_receipt_hmac="b" * 64,
            expires_at_utc=receipt.expires_at_utc,
        ),
        CorpusMaterializationErrorCode.READY_CONFLICT,
    )
    _expect_error(
        lambda: service.consume_ready(
            owner_key="owner-a",
            receipt=receipt,
            ready_receipt_hmac=ready_hmac,
            operation_id="invalid-operation",
        ),
        CorpusMaterializationErrorCode.READY_REJECTED,
    )
    service.cleanup(owner_key="owner-a", receipt=receipt)
    assert workspaces.list_layouts() == ()

    expired, expired_workspaces, _ = _environment(tmp_path / "expired-bind")
    expired_receipt = expired.materialize(owner_key="owner-a", payloads=(source,))
    _expect_error(
        lambda: expired.bind_ready(
            owner_key="owner-a",
            receipt=expired_receipt,
            ready_receipt_hmac=ready_hmac,
            expires_at_utc=NOW,
        ),
        CorpusMaterializationErrorCode.EXPIRED,
    )
    assert expired_workspaces.list_layouts() == ()

    bind_failure, bind_workspaces, _ = _environment(tmp_path / "bind-failure")
    bind_receipt = bind_failure.materialize(owner_key="owner-a", payloads=(source,))

    def fail_bind(**_kwargs) -> None:
        raise RuntimeError("private ready boundary corpus")

    monkeypatch.setattr(bind_failure._jobs, "bind_analysis_admission", fail_bind)
    _expect_error(
        lambda: bind_failure.bind_ready(
            owner_key="owner-a",
            receipt=bind_receipt,
            ready_receipt_hmac=ready_hmac,
            expires_at_utc=bind_receipt.expires_at_utc,
        ),
        CorpusMaterializationErrorCode.READY_REJECTED,
    )
    bind_failure.cleanup(owner_key="owner-a", receipt=bind_receipt)
    assert bind_workspaces.list_layouts() == ()

    service_failure, service_workspaces, _ = _environment(tmp_path / "service-bind-failure")
    service_receipt = service_failure.materialize(owner_key="owner-a", payloads=(source,))

    def reject_bind(**_kwargs) -> None:
        raise JobServiceError(JobServiceErrorCode.ANALYSIS_ADMISSION_REJECTED)

    monkeypatch.setattr(service_failure._jobs, "bind_analysis_admission", reject_bind)
    _expect_error(
        lambda: service_failure.bind_ready(
            owner_key="owner-a",
            receipt=service_receipt,
            ready_receipt_hmac=ready_hmac,
            expires_at_utc=service_receipt.expires_at_utc,
        ),
        CorpusMaterializationErrorCode.READY_REJECTED,
    )
    service_failure.cleanup(owner_key="owner-a", receipt=service_receipt)
    assert service_workspaces.list_layouts() == ()


def test_ready_status_and_consume_translate_downstream_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(1, b"private downstream corpus")
    service, workspaces, _clock = _environment(tmp_path)
    receipt = service.materialize(owner_key="owner-a", payloads=(source,))
    ready_hmac = "c" * 64
    service.bind_ready(
        owner_key="owner-a",
        receipt=receipt,
        ready_receipt_hmac=ready_hmac,
        expires_at_utc=receipt.expires_at_utc,
    )
    original_consume = service._jobs.consume_analysis_admission

    def rejected_consume(**_kwargs):
        raise JobServiceError(JobServiceErrorCode.ANALYSIS_ADMISSION_REJECTED)

    monkeypatch.setattr(service._jobs, "consume_analysis_admission", rejected_consume)
    _expect_error(
        lambda: service.consume_ready(
            owner_key="owner-a",
            receipt=receipt,
            ready_receipt_hmac=ready_hmac,
            operation_id="op_" + "d" * 64,
        ),
        CorpusMaterializationErrorCode.READY_REJECTED,
    )

    def broken_consume(**_kwargs):
        raise RuntimeError("private downstream corpus")

    monkeypatch.setattr(service._jobs, "consume_analysis_admission", broken_consume)
    _expect_error(
        lambda: service.consume_ready(
            owner_key="owner-a",
            receipt=receipt,
            ready_receipt_hmac=ready_hmac,
            operation_id="op_" + "d" * 64,
        ),
        CorpusMaterializationErrorCode.READY_REJECTED,
    )
    monkeypatch.setattr(service._jobs, "consume_analysis_admission", original_consume)
    original_status = service._jobs.status

    def broken_status(**_kwargs):
        raise RuntimeError("private downstream corpus")

    monkeypatch.setattr(service._jobs, "status", broken_status)
    _expect_error(
        lambda: service.status(owner_key="owner-a", receipt=receipt),
        CorpusMaterializationErrorCode.NOT_AVAILABLE,
    )
    monkeypatch.setattr(service._jobs, "status", original_status)
    service.cleanup(owner_key="owner-a", receipt=receipt)
    assert workspaces.list_layouts() == ()

    reused, reused_workspaces, _ = _environment(tmp_path / "reused")
    reused_receipt = reused.materialize(owner_key="owner-a", payloads=(source,))
    reused.bind_ready(
        owner_key="owner-a",
        receipt=reused_receipt,
        ready_receipt_hmac=ready_hmac,
        expires_at_utc=reused_receipt.expires_at_utc,
    )

    def reused_consume(**_kwargs):
        raise JobServiceError(JobServiceErrorCode.ANALYSIS_ADMISSION_REUSED)

    monkeypatch.setattr(reused._jobs, "consume_analysis_admission", reused_consume)
    _expect_error(
        lambda: reused.consume_ready(
            owner_key="owner-a",
            receipt=reused_receipt,
            ready_receipt_hmac=ready_hmac,
            operation_id="op_" + "e" * 64,
        ),
        CorpusMaterializationErrorCode.READY_REUSED,
    )
    assert reused._leases[reused_receipt.lease_id].consumed is True
    assert len(reused_workspaces.list_layouts()) == 1


def test_status_invalid_clock_cleans_unconsumed_materialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, workspaces, _clock = _environment(tmp_path)
    source = _source(1, b"private status clock corpus")
    receipt = service.materialize(owner_key="owner-a", payloads=(source,))

    class BrokenClock:
        def now(self) -> datetime:
            raise RuntimeError("private status clock corpus")

    monkeypatch.setattr(service, "_clock", BrokenClock())
    _expect_error(
        lambda: service.status(owner_key="owner-a", receipt=receipt),
        CorpusMaterializationErrorCode.INVALID_CONFIGURATION,
    )
    assert workspaces.list_layouts() == ()
