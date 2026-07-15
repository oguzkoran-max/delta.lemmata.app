"""Public P007 preparation facade over private P005 corpus materialization."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from functools import wraps
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from delta_lemmata.clock import Clock, require_utc
from delta_lemmata.corpus_health import WorkHealthContext, assess_corpus_health
from delta_lemmata.corpus_health_models import CorpusHealthReadiness, CorpusHealthReportV1
from delta_lemmata.corpus_materialization import (
    CorpusMaterializationError,
    CorpusMaterializationErrorCode,
    CorpusMaterializationReceipt,
    CorpusMaterializationService,
)
from delta_lemmata.corpus_models import DateValue
from delta_lemmata.corpus_validation import ValidationReport, validate_inventory
from delta_lemmata.ingestion import ValidatedCorpusPayload
from delta_lemmata.inventory import CorpusInventory, inventory_sha256
from delta_lemmata.job_ui import JobPresentation
from delta_lemmata.job_workspace import WorkspaceArea, WorkspaceLayout, WorkspaceManager
from delta_lemmata.preprocessing import (
    CandidateInventory,
    CustomExclusions,
    PreparedDocument,
    build_candidate_inventory,
    build_preprocessing_config,
    build_preprocessing_manifest,
    parse_custom_exclusions,
    prepare_document,
)
from delta_lemmata.preprocessing_models import (
    AnalysisPreparationReceiptV1,
    CorpusAnalysisAnnotationsV1,
    PreparationState,
    PreprocessingConfigV1,
    PreprocessingManifestV1,
    ReceiptDocumentBinding,
    canonical_p007_json,
)
from delta_lemmata.session_identity import MINIMUM_OWNER_SECRET_BYTES
from delta_lemmata.stylo_contracts import INPUT_MAX_BYTES, WorkerInputV1, canonical_worker_json
from delta_lemmata.stylo_input_builder import _build_guided_worker_input
from delta_lemmata.workflow_models import (
    MAX_WORKFLOW_CONFIG_BYTES,
    P008ContractError,
    ResolvedWorkflowConfigV1,
    canonical_p008_json,
    parse_resolved_workflow_config,
    workflow_config_sha256,
)

ReceiptIdFactory = Callable[[], str]
EntropyFactory = Callable[[int], bytes]

_HEX_64 = re.compile(r"^[0-9a-f]{64}$", flags=re.ASCII)
_AUTHORITY_DOMAIN = b"delta-lemmata\x00p007-prepared-corpus-authority\x00v1\x00"
_RECEIPT_DOMAIN = b"ready-receipt-hmac-v1"
_REQUEST_DOMAIN = b"worker-request-id-v1"
_REFERENCE_DOMAIN = b"worker-reference-key-v1"
_REQUEST_COMPONENT_DOMAIN = b"worker-request-component-v1"
_WORKFLOW_COMPONENT_DOMAIN = b"resolved-workflow-component-v1"
_OPERATION_DOMAIN = b"analysis-admission-operation-v1"
_INDEX_DOMAIN = b"delta-lemmata\x00prepared-request-index\x00v2"
PREPARED_REQUEST_INDEX_COMPONENT = hashlib.sha256(_INDEX_DOMAIN).hexdigest()
PREPARED_REQUEST_INDEX_MAX_BYTES = 2048


class PreparedCorpusErrorCode(StrEnum):
    INVALID_CONFIGURATION = "P007_PREPARED_CORPUS_INVALID_CONFIGURATION"
    INVALID_REQUEST = "P007_PREPARED_CORPUS_INVALID_REQUEST"
    P004_BLOCKED = "P007_PREPARED_CORPUS_P004_BLOCKED"
    RIGHTS_BLOCKED = "P007_PREPARED_CORPUS_RIGHTS_BLOCKED"
    BINDING_MISMATCH = "P007_PREPARED_CORPUS_BINDING_MISMATCH"
    EXPIRED = "P007_PREPARED_CORPUS_EXPIRED"
    NOT_AVAILABLE = "P007_PREPARED_CORPUS_NOT_AVAILABLE"
    ALREADY_READY = "P007_PREPARED_CORPUS_ALREADY_READY"
    ADMISSION_REJECTED = "P007_PREPARED_CORPUS_ADMISSION_REJECTED"
    ADMISSION_REUSED = "P007_PREPARED_CORPUS_ADMISSION_REUSED"
    INTEGRITY = "P007_PREPARED_CORPUS_INTEGRITY"
    CLEANUP_FAILED = "P007_PREPARED_CORPUS_CLEANUP_FAILED"
    OPERATION_FAILED = "P007_PREPARED_CORPUS_OPERATION_FAILED"


class PreparedCorpusError(RuntimeError):
    """Content-free failure at the public preparation facade."""

    def __init__(self, code: PreparedCorpusErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class PreparationOutcome:
    """Payload-free P007 report set safe for the presentation workflow."""

    validation_report: ValidationReport
    config: PreprocessingConfigV1
    manifest: PreprocessingManifestV1
    health_report: CorpusHealthReportV1
    ready_receipt: AnalysisPreparationReceiptV1 | None
    readiness_scope: Literal["computational_preflight_only"] = "computational_preflight_only"


@dataclass(frozen=True, slots=True)
class _PreparationBundle:
    validation_report: ValidationReport
    config: PreprocessingConfigV1
    manifest: PreprocessingManifestV1
    health_report: CorpusHealthReportV1
    documents: tuple[PreparedDocument, ...] = field(repr=False)
    candidates: CandidateInventory = field(repr=False)


class PreparedRequestIndexV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["prepared-stylo-request-index-v2"]
    request_component: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_byte_count: int = Field(ge=1, le=INPUT_MAX_BYTES)
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    workflow_config_component: str = Field(pattern=r"^[0-9a-f]{64}$")
    workflow_config_byte_count: int = Field(ge=1, le=MAX_WORKFLOW_CONFIG_BYTES)
    workflow_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _detach(error: PreparedCorpusError) -> None:
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True


def _error(code: PreparedCorpusErrorCode) -> PreparedCorpusError:
    error = PreparedCorpusError(code)
    _detach(error)
    return error


def _content_free[**P, ResultT](method: Callable[P, ResultT]) -> Callable[P, ResultT]:
    @wraps(method)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResultT:
        try:
            return method(*args, **kwargs)
        except PreparedCorpusError as error:
            rejection = error
        except Exception:
            rejection = PreparedCorpusError(PreparedCorpusErrorCode.OPERATION_FAILED)
        _detach(rejection)
        raise rejection

    return wrapped


def _frame(domain: bytes, *values: bytes) -> bytes:
    framed = bytearray(_AUTHORITY_DOMAIN)
    for value in (domain, *values):
        framed.extend(len(value).to_bytes(4, byteorder="big"))
        framed.extend(value)
    return bytes(framed)


def _authority(secret: bytes, domain: bytes, *values: bytes) -> bytes:
    return hmac.digest(secret, _frame(domain, *values), "sha256")


def _chronology_point(value: DateValue) -> str | None:
    if value.start_year is None:
        return None
    end = "" if value.end_year is None else str(value.end_year)
    return f"{value.mode.value}:{value.start_year}:{end}"


def _binding(document: PreparedDocument) -> ReceiptDocumentBinding:
    annotation = document.annotation
    return ReceiptDocumentBinding(
        document_id=annotation.document_id,
        asset_id=annotation.asset_id,
        work_id=annotation.work_id,
        analysis_role=annotation.analysis_role,
    )


def canonical_prepared_request_index(index: PreparedRequestIndexV2) -> bytes:
    return json.dumps(
        index.model_dump(mode="json"),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


class PreparedCorpusService:
    """Prepare, bind, and admit one corpus without returning private analysis data."""

    @_content_free
    def __init__(
        self,
        *,
        materializations: CorpusMaterializationService,
        workspaces: WorkspaceManager,
        clock: Clock,
        authority_secret: bytes,
        receipt_id_factory: ReceiptIdFactory | None = None,
        entropy_factory: EntropyFactory = secrets.token_bytes,
    ) -> None:
        if (
            not isinstance(materializations, CorpusMaterializationService)
            or not isinstance(workspaces, WorkspaceManager)
            or not hasattr(clock, "now")
            or not isinstance(authority_secret, bytes)
            or len(authority_secret) < MINIMUM_OWNER_SECRET_BYTES
            or (receipt_id_factory is not None and not callable(receipt_id_factory))
            or not callable(entropy_factory)
        ):
            raise _error(PreparedCorpusErrorCode.INVALID_CONFIGURATION)
        self._materializations = materializations
        self._workspaces = workspaces
        self._clock = clock
        self._authority_secret = authority_secret
        self._receipt_id_factory = receipt_id_factory or (lambda: secrets.token_hex(32))
        self._entropy_factory = entropy_factory

    def _now(self) -> datetime:
        try:
            return require_utc(self._clock.now(), field_name="prepared corpus clock")
        except Exception:
            raise _error(PreparedCorpusErrorCode.INVALID_CONFIGURATION) from None

    def _receipt_id(self) -> str:
        try:
            value = self._receipt_id_factory()
        except Exception:
            raise _error(PreparedCorpusErrorCode.INVALID_CONFIGURATION) from None
        if not isinstance(value, str) or _HEX_64.fullmatch(value) is None:
            raise _error(PreparedCorpusErrorCode.INVALID_CONFIGURATION)
        return "receipt_" + value

    def _entropy(self) -> bytes:
        try:
            value = self._entropy_factory(32)
        except Exception:
            raise _error(PreparedCorpusErrorCode.INVALID_CONFIGURATION) from None
        if not isinstance(value, bytes) or len(value) != 32:
            raise _error(PreparedCorpusErrorCode.INVALID_CONFIGURATION)
        return value

    def _receipt_hmac(self, receipt: AnalysisPreparationReceiptV1) -> str:
        return _authority(
            self._authority_secret,
            _RECEIPT_DOMAIN,
            canonical_p007_json(receipt),
        ).hex()

    def _cleanup(
        self,
        *,
        owner_key: str,
        materialization_receipt: CorpusMaterializationReceipt,
    ) -> None:
        try:
            self._materializations.cleanup(
                owner_key=owner_key,
                receipt=materialization_receipt,
            )
        except Exception:
            raise _error(PreparedCorpusErrorCode.CLEANUP_FAILED) from None

    @staticmethod
    def _validate_public_inputs(
        *,
        inventory: CorpusInventory,
        annotations: CorpusAnalysisAnnotationsV1,
        config: PreprocessingConfigV1,
        exclusions: CustomExclusions,
    ) -> ValidationReport:
        if (
            not isinstance(inventory, CorpusInventory)
            or not isinstance(annotations, CorpusAnalysisAnnotationsV1)
            or not isinstance(config, PreprocessingConfigV1)
            or not isinstance(exclusions, CustomExclusions)
        ):
            raise _error(PreparedCorpusErrorCode.INVALID_REQUEST)
        validation = validate_inventory(inventory)
        if validation.blocked:
            raise _error(PreparedCorpusErrorCode.P004_BLOCKED)
        digest = inventory_sha256(inventory)
        if validation.inventory_sha256 != digest or annotations.inventory_sha256 != digest:
            raise _error(PreparedCorpusErrorCode.BINDING_MISMATCH)
        if config != build_preprocessing_config(exclusions):
            raise _error(PreparedCorpusErrorCode.BINDING_MISMATCH)
        rights_by_id = {item.asset_id: item for item in inventory.rights}
        if any(
            not asset.rights_chain_confirmed
            or asset.asset_id not in asset.rights_asset_ids
            or any(
                (rights := rights_by_id.get(rights_id)) is None or not rights.allows_analysis
                for rights_id in asset.rights_asset_ids
            )
            for asset in inventory.assets
        ):
            raise _error(PreparedCorpusErrorCode.RIGHTS_BLOCKED)
        return validation

    @staticmethod
    def _bundle(
        *,
        payloads: tuple[ValidatedCorpusPayload, ...],
        inventory: CorpusInventory,
        annotations: CorpusAnalysisAnnotationsV1,
        config: PreprocessingConfigV1,
        exclusions: CustomExclusions,
        validation_report: ValidationReport,
    ) -> _PreparationBundle:
        payload_by_key = {
            (item.receipt.display_label, item.receipt.sha256): item for item in payloads
        }
        validated_by_key = {
            (item.file_label, item.content_sha256): item for item in inventory.validated_files
        }
        assets_by_id = {item.asset_id: item for item in inventory.assets}
        if (
            len(payload_by_key) != len(payloads)
            or len(validated_by_key) != len(inventory.validated_files)
            or len(assets_by_id) != len(inventory.assets)
            or {item.asset_id for item in annotations.annotations} != set(assets_by_id)
            or len(payloads) != len(inventory.assets)
        ):
            raise _error(PreparedCorpusErrorCode.BINDING_MISMATCH)

        documents: list[PreparedDocument] = []
        for annotation in annotations.annotations:
            asset = assets_by_id.get(annotation.asset_id)
            if asset is None or asset.work_id != annotation.work_id:
                raise _error(PreparedCorpusErrorCode.BINDING_MISMATCH)
            key = (asset.file_label, asset.content_sha256)
            payload = payload_by_key.get(key)
            validated = validated_by_key.get(key)
            if (
                payload is None
                or validated is None
                or payload.receipt.limit_profile != validated.intake_profile
                or payload.receipt.byte_size != len(payload.content)
            ):
                raise _error(PreparedCorpusErrorCode.BINDING_MISMATCH)
            documents.append(
                prepare_document(
                    payload.content,
                    expected_raw_sha256=asset.content_sha256,
                    annotation=annotation,
                )
            )
        prepared = tuple(documents)
        candidates = build_candidate_inventory(prepared, exclusions=exclusions)
        manifest = build_preprocessing_manifest(
            config=config,
            annotations=annotations,
            documents=prepared,
            candidate_inventory=candidates,
        )
        works_by_id = {item.work_id: item for item in inventory.works}
        editions_by_id = {item.edition_id: item for item in inventory.editions}
        sources_by_id = {item.source_id: item for item in inventory.sources}
        contexts = tuple(
            WorkHealthContext(
                work_id=annotation.work_id,
                group_label=works_by_id[annotation.work_id].group_label,
                chronology_point=_chronology_point(
                    works_by_id[annotation.work_id].first_publication
                ),
                chronology_certainty=works_by_id[annotation.work_id].first_publication.mode.value,
                edition_context=editions_by_id[
                    assets_by_id[annotation.asset_id].edition_id
                ].edition_label,
                genre=works_by_id[annotation.work_id].genre.value,
                audience=works_by_id[annotation.work_id].audience.value,
                source_type=sources_by_id[
                    assets_by_id[annotation.asset_id].source_id
                ].source_type.value,
                adaptation=works_by_id[annotation.work_id].adaptation.value,
                collection=works_by_id[annotation.work_id].collection.value,
                ocr_status=annotation.ocr_status.value,
                paratext_status=annotation.paratext_status.value,
                curation_state=(
                    "disclosed"
                    if annotation.preupload_curation_note is not None
                    else "not_disclosed"
                ),
            )
            for annotation in annotations.annotations
        )
        health = assess_corpus_health(
            purpose=inventory.purpose,
            config=config,
            annotations=annotations,
            manifest=manifest,
            documents=prepared,
            candidate_inventory=candidates,
            work_contexts=contexts,
        )
        return _PreparationBundle(
            validation_report=validation_report,
            config=config,
            manifest=manifest,
            health_report=health,
            documents=prepared,
            candidates=candidates,
        )

    def _public_setup(
        self,
        *,
        inventory: CorpusInventory,
        annotations: CorpusAnalysisAnnotationsV1,
        config: PreprocessingConfigV1,
        custom_exclusions_bytes: bytes | None,
    ) -> tuple[CustomExclusions, ValidationReport]:
        try:
            exclusions = parse_custom_exclusions(custom_exclusions_bytes)
        except Exception:
            raise _error(PreparedCorpusErrorCode.INVALID_REQUEST) from None
        validation = self._validate_public_inputs(
            inventory=inventory,
            annotations=annotations,
            config=config,
            exclusions=exclusions,
        )
        return exclusions, validation

    def _map_materialization_error(
        self,
        error: CorpusMaterializationError,
    ) -> PreparedCorpusError:
        if error.code is CorpusMaterializationErrorCode.EXPIRED:
            return _error(PreparedCorpusErrorCode.EXPIRED)
        if error.code in {
            CorpusMaterializationErrorCode.NOT_AVAILABLE,
            CorpusMaterializationErrorCode.INVALID_REQUEST,
        }:
            return _error(PreparedCorpusErrorCode.NOT_AVAILABLE)
        if error.code is CorpusMaterializationErrorCode.READY_REUSED:
            return _error(PreparedCorpusErrorCode.ADMISSION_REUSED)
        if error.code is CorpusMaterializationErrorCode.READY_CONFLICT:
            return _error(PreparedCorpusErrorCode.ALREADY_READY)
        if error.code is CorpusMaterializationErrorCode.READY_REJECTED:
            return _error(PreparedCorpusErrorCode.ADMISSION_REJECTED)
        return _error(PreparedCorpusErrorCode.INTEGRITY)

    @_content_free
    def prepare(
        self,
        *,
        owner_key: str,
        materialization_receipt: CorpusMaterializationReceipt,
        inventory: CorpusInventory,
        annotations: CorpusAnalysisAnnotationsV1,
        config: PreprocessingConfigV1,
        custom_exclusions_bytes: bytes | None = None,
    ) -> PreparationOutcome:
        """Prepare one bound corpus and return a READY receipt only when unblocked."""

        if not isinstance(materialization_receipt, CorpusMaterializationReceipt):
            raise _error(PreparedCorpusErrorCode.INVALID_REQUEST)
        try:
            exclusions, validation = self._public_setup(
                inventory=inventory,
                annotations=annotations,
                config=config,
                custom_exclusions_bytes=custom_exclusions_bytes,
            )
        except PreparedCorpusError:
            self._cleanup(
                owner_key=owner_key,
                materialization_receipt=materialization_receipt,
            )
            raise
        try:
            bundle = self._materializations.visit(
                owner_key=owner_key,
                receipt=materialization_receipt,
                visitor=lambda payloads: self._bundle(
                    payloads=payloads,
                    inventory=inventory,
                    annotations=annotations,
                    config=config,
                    exclusions=exclusions,
                    validation_report=validation,
                ),
            )
        except CorpusMaterializationError as error:
            raise self._map_materialization_error(error) from None
        if bundle.health_report.blocker_count != 0:
            self._cleanup(
                owner_key=owner_key,
                materialization_receipt=materialization_receipt,
            )
            return PreparationOutcome(
                validation_report=validation,
                config=config,
                manifest=bundle.manifest,
                health_report=bundle.health_report,
                ready_receipt=None,
            )

        try:
            issued_at = self._now()
            expires_at = min(
                materialization_receipt.expires_at_utc,
                issued_at + timedelta(hours=1),
            )
            if issued_at >= expires_at:
                raise _error(PreparedCorpusErrorCode.EXPIRED)
            nonce = self._entropy()
            receipt = AnalysisPreparationReceiptV1(
                schema_version="analysis-preparation-receipt-v1",
                receipt_id=self._receipt_id(),
                state=PreparationState.READY,
                issued_at_utc=issued_at,
                expires_at_utc=expires_at,
                admission_nonce_sha256=hashlib.sha256(nonce).hexdigest(),
                inventory_sha256=inventory_sha256(inventory),
                validation_report_sha256=hashlib.sha256(
                    canonical_p007_json(validation)
                ).hexdigest(),
                annotations_sha256=hashlib.sha256(canonical_p007_json(annotations)).hexdigest(),
                config_sha256=hashlib.sha256(canonical_p007_json(config)).hexdigest(),
                manifest_sha256=hashlib.sha256(canonical_p007_json(bundle.manifest)).hexdigest(),
                health_report_sha256=hashlib.sha256(
                    canonical_p007_json(bundle.health_report)
                ).hexdigest(),
                candidate_inventory_sha256=bundle.candidates.sha256,
                candidate_feature_count=len(bundle.candidates.features),
                blocker_count=0,
                ordered_documents=tuple(_binding(item) for item in bundle.documents),
            )
            receipt_hmac = self._receipt_hmac(receipt)
            self._materializations.bind_ready(
                owner_key=owner_key,
                receipt=materialization_receipt,
                ready_receipt_hmac=receipt_hmac,
                expires_at_utc=expires_at,
            )
        except CorpusMaterializationError as error:
            if error.code not in {
                CorpusMaterializationErrorCode.EXPIRED,
                CorpusMaterializationErrorCode.READY_CONFLICT,
                CorpusMaterializationErrorCode.READY_REUSED,
            }:
                self._cleanup(
                    owner_key=owner_key,
                    materialization_receipt=materialization_receipt,
                )
            raise self._map_materialization_error(error) from None
        except PreparedCorpusError:
            self._cleanup(
                owner_key=owner_key,
                materialization_receipt=materialization_receipt,
            )
            raise
        except Exception:
            self._cleanup(
                owner_key=owner_key,
                materialization_receipt=materialization_receipt,
            )
            raise _error(PreparedCorpusErrorCode.OPERATION_FAILED) from None
        return PreparationOutcome(
            validation_report=validation,
            config=config,
            manifest=bundle.manifest,
            health_report=bundle.health_report,
            ready_receipt=receipt,
        )

    def _verify_receipt(
        self,
        *,
        receipt: AnalysisPreparationReceiptV1,
        inventory: CorpusInventory,
        annotations: CorpusAnalysisAnnotationsV1,
        config: PreprocessingConfigV1,
        bundle: _PreparationBundle,
    ) -> None:
        expected = {
            "inventory_sha256": inventory_sha256(inventory),
            "validation_report_sha256": hashlib.sha256(
                canonical_p007_json(bundle.validation_report)
            ).hexdigest(),
            "annotations_sha256": hashlib.sha256(canonical_p007_json(annotations)).hexdigest(),
            "config_sha256": hashlib.sha256(canonical_p007_json(config)).hexdigest(),
            "manifest_sha256": hashlib.sha256(canonical_p007_json(bundle.manifest)).hexdigest(),
            "health_report_sha256": hashlib.sha256(
                canonical_p007_json(bundle.health_report)
            ).hexdigest(),
            "candidate_inventory_sha256": bundle.candidates.sha256,
            "candidate_feature_count": len(bundle.candidates.features),
            "ordered_documents": tuple(_binding(item) for item in bundle.documents),
        }
        if (
            receipt.state is not PreparationState.READY
            or receipt.blocker_count != 0
            or bundle.health_report.readiness is not CorpusHealthReadiness.READY
            or any(getattr(receipt, field_name) != value for field_name, value in expected.items())
        ):
            raise _error(PreparedCorpusErrorCode.BINDING_MISMATCH)

    def _request_identity(
        self,
        receipt_hmac: str,
        resolved_config_sha256: str,
    ) -> tuple[str, bytes, str, str, str]:
        if (
            not isinstance(receipt_hmac, str)
            or _HEX_64.fullmatch(receipt_hmac) is None
            or not isinstance(resolved_config_sha256, str)
            or _HEX_64.fullmatch(resolved_config_sha256) is None
        ):
            raise _error(PreparedCorpusErrorCode.INVALID_REQUEST)
        encoded = receipt_hmac.encode("ascii")
        config_digest = resolved_config_sha256.encode("ascii")
        request_id = (
            "request_"
            + _authority(
                self._authority_secret,
                _REQUEST_DOMAIN,
                encoded,
                config_digest,
            ).hex()
        )
        reference_key = _authority(
            self._authority_secret,
            _REFERENCE_DOMAIN,
            encoded,
            config_digest,
        )
        request_component = _authority(
            self._authority_secret,
            _REQUEST_COMPONENT_DOMAIN,
            encoded,
            config_digest,
        ).hex()
        workflow_config_component = _authority(
            self._authority_secret,
            _WORKFLOW_COMPONENT_DOMAIN,
            encoded,
            config_digest,
        ).hex()
        operation_id = (
            "op_"
            + _authority(
                self._authority_secret,
                _OPERATION_DOMAIN,
                encoded,
                config_digest,
            ).hex()
        )
        return (
            request_id,
            reference_key,
            request_component,
            workflow_config_component,
            operation_id,
        )

    def _create_or_verify(
        self,
        *,
        layout: WorkspaceLayout,
        component: str,
        payload: bytes,
        maximum_bytes: int,
    ) -> None:
        existing = self._workspaces.read_file(
            layout,
            WorkspaceArea.WORK,
            component,
            maximum_bytes=maximum_bytes,
        )
        if existing is not None:
            if existing != payload:
                raise _error(PreparedCorpusErrorCode.INTEGRITY)
            return
        create_conflict = False
        try:
            self._workspaces.create_file(
                layout,
                WorkspaceArea.WORK,
                component,
                payload,
            )
        except Exception:
            existing = self._workspaces.read_file(
                layout,
                WorkspaceArea.WORK,
                component,
                maximum_bytes=maximum_bytes,
            )
            if existing != payload:
                create_conflict = True
        if create_conflict:
            raise _error(PreparedCorpusErrorCode.INTEGRITY)

    def _store_request(
        self,
        *,
        layout: WorkspaceLayout,
        request: WorkerInputV1,
        request_component: str,
        resolved_workflow_config: ResolvedWorkflowConfigV1,
        workflow_config_component: str,
    ) -> None:
        request_payload = canonical_worker_json(request)
        workflow_config_payload = canonical_p008_json(resolved_workflow_config)
        index = PreparedRequestIndexV2(
            schema_version="prepared-stylo-request-index-v2",
            request_component=request_component,
            request_byte_count=len(request_payload),
            request_sha256=hashlib.sha256(request_payload).hexdigest(),
            workflow_config_component=workflow_config_component,
            workflow_config_byte_count=len(workflow_config_payload),
            workflow_config_sha256=hashlib.sha256(workflow_config_payload).hexdigest(),
        )
        expected_index = canonical_prepared_request_index(index)
        existing_index = self._workspaces.read_file(
            layout,
            WorkspaceArea.WORK,
            PREPARED_REQUEST_INDEX_COMPONENT,
            maximum_bytes=PREPARED_REQUEST_INDEX_MAX_BYTES,
        )
        if existing_index is not None:
            try:
                parsed = PreparedRequestIndexV2.model_validate_json(existing_index)
            except ValidationError:
                raise _error(PreparedCorpusErrorCode.INTEGRITY) from None
            existing_request = self._workspaces.read_file(
                layout,
                WorkspaceArea.WORK,
                parsed.request_component,
                maximum_bytes=INPUT_MAX_BYTES,
            )
            existing_workflow_config = self._workspaces.read_file(
                layout,
                WorkspaceArea.WORK,
                parsed.workflow_config_component,
                maximum_bytes=MAX_WORKFLOW_CONFIG_BYTES,
            )
            if (
                parsed != index
                or existing_index != expected_index
                or existing_request != request_payload
                or existing_workflow_config != workflow_config_payload
            ):
                raise _error(PreparedCorpusErrorCode.INTEGRITY)
            return
        self._create_or_verify(
            layout=layout,
            component=request_component,
            payload=request_payload,
            maximum_bytes=INPUT_MAX_BYTES,
        )
        self._create_or_verify(
            layout=layout,
            component=workflow_config_component,
            payload=workflow_config_payload,
            maximum_bytes=MAX_WORKFLOW_CONFIG_BYTES,
        )
        self._create_or_verify(
            layout=layout,
            component=PREPARED_REQUEST_INDEX_COMPONENT,
            payload=expected_index,
            maximum_bytes=PREPARED_REQUEST_INDEX_MAX_BYTES,
        )

    @_content_free
    def admit_once(
        self,
        *,
        owner_key: str,
        materialization_receipt: CorpusMaterializationReceipt,
        ready_receipt: AnalysisPreparationReceiptV1,
        inventory: CorpusInventory,
        annotations: CorpusAnalysisAnnotationsV1,
        config: PreprocessingConfigV1,
        resolved_workflow_config: ResolvedWorkflowConfigV1,
        custom_exclusions_bytes: bytes | None = None,
    ) -> JobPresentation:
        """Rebuild all bindings, persist one private request, and enqueue exactly once."""

        if (
            not isinstance(materialization_receipt, CorpusMaterializationReceipt)
            or not isinstance(ready_receipt, AnalysisPreparationReceiptV1)
            or not isinstance(resolved_workflow_config, ResolvedWorkflowConfigV1)
        ):
            raise _error(PreparedCorpusErrorCode.INVALID_REQUEST)
        try:
            checked_workflow_config = parse_resolved_workflow_config(
                canonical_p008_json(resolved_workflow_config)
            )
        except P008ContractError:
            raise _error(PreparedCorpusErrorCode.BINDING_MISMATCH) from None
        if checked_workflow_config.purpose is not inventory.purpose:
            raise _error(PreparedCorpusErrorCode.BINDING_MISMATCH)
        exclusions, validation = self._public_setup(
            inventory=inventory,
            annotations=annotations,
            config=config,
            custom_exclusions_bytes=custom_exclusions_bytes,
        )
        receipt_hmac = self._receipt_hmac(ready_receipt)
        resolved_config_sha256 = workflow_config_sha256(resolved_workflow_config)
        (
            request_id,
            reference_key,
            request_component,
            workflow_config_component,
            operation_id,
        ) = self._request_identity(
            receipt_hmac,
            resolved_config_sha256,
        )

        def prepare_private_request(
            payloads: tuple[ValidatedCorpusPayload, ...],
            layout: WorkspaceLayout,
        ) -> None:
            bundle = self._bundle(
                payloads=payloads,
                inventory=inventory,
                annotations=annotations,
                config=config,
                exclusions=exclusions,
                validation_report=validation,
            )
            self._verify_receipt(
                receipt=ready_receipt,
                inventory=inventory,
                annotations=annotations,
                config=config,
                bundle=bundle,
            )
            request = _build_guided_worker_input(
                receipt=ready_receipt,
                documents=bundle.documents,
                candidate_inventory=bundle.candidates,
                resolved_config=resolved_workflow_config,
                request_id=request_id,
                reference_key=reference_key,
                at_utc=self._now(),
            )
            self._store_request(
                layout=layout,
                request=request,
                request_component=request_component,
                resolved_workflow_config=resolved_workflow_config,
                workflow_config_component=workflow_config_component,
            )

        try:
            self._materializations._visit_workspace(
                owner_key=owner_key,
                receipt=materialization_receipt,
                visitor=prepare_private_request,
                ready_receipt_hmac=receipt_hmac,
            )
            return self._materializations.consume_ready(
                owner_key=owner_key,
                receipt=materialization_receipt,
                ready_receipt_hmac=receipt_hmac,
                operation_id=operation_id,
            )
        except CorpusMaterializationError as error:
            raise self._map_materialization_error(error) from None

    @_content_free
    def status(
        self,
        *,
        owner_key: str,
        materialization_receipt: CorpusMaterializationReceipt,
    ) -> JobPresentation:
        """Return the owned P005 job projection after preparation or admission."""

        try:
            return self._materializations.status(
                owner_key=owner_key,
                receipt=materialization_receipt,
            )
        except CorpusMaterializationError as error:
            raise self._map_materialization_error(error) from None


__all__ = [
    "PREPARED_REQUEST_INDEX_COMPONENT",
    "PREPARED_REQUEST_INDEX_MAX_BYTES",
    "PreparationOutcome",
    "PreparedCorpusError",
    "PreparedCorpusErrorCode",
    "PreparedCorpusService",
    "PreparedRequestIndexV2",
    "canonical_prepared_request_index",
]
