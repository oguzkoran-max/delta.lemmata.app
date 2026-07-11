"""Action-specific rights documentation contracts for P004."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal, Self

from pydantic import ConfigDict, Field, HttpUrl, TypeAdapter, model_validator

from delta_lemmata.corpus_models import ASSET_ID_PATTERN, SLUG_PATTERN, FrozenModel


class PermissionState(StrEnum):
    PERMITTED = "permitted"
    PROHIBITED = "prohibited"
    UNKNOWN = "unknown"


class RightsStatus(StrEnum):
    VERIFIED_OPEN = "verified_open"
    ANALYSIS_ONLY = "analysis_only"
    PERMISSION_REQUIRED = "permission_required"
    UNKNOWN = "unknown"
    EXCLUDED = "excluded"


class AssetType(StrEnum):
    UNDERLYING_WORK = "underlying_work"
    EDITION = "edition"
    SCAN = "scan"
    TRANSCRIPTION = "transcription"
    MARKUP = "markup"
    ANNOTATION = "annotation"
    NORMALIZED_TEXT = "normalized_text"
    DERIVED_OUTPUT = "derived_output"


class ActionPermissions(FrozenModel):
    upload: PermissionState
    analysis: PermissionState
    export: PermissionState
    public_redistribution: PermissionState


class RightsEvidence(FrozenModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "if": {
                "properties": {"evidence_type": {"const": "url"}},
                "required": ["evidence_type"],
            },
            "then": {
                "properties": {
                    "value": {
                        "format": "uri",
                        "pattern": r"^https?://[^\s]+$",
                    }
                },
            },
        },
    )

    evidence_type: Literal["url", "citation", "statement"]
    value: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_web_url_for_url_evidence(self) -> Self:
        if self.evidence_type == "url":
            TypeAdapter(HttpUrl).validate_python(self.value)
        return self


class AssetRightsRecord(FrozenModel):
    """A human-confirmed record, not an automated legal conclusion."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "allOf": [
                {
                    "if": {
                        "properties": {
                            "permissions": {
                                "properties": {"public_redistribution": {"const": "permitted"}},
                                "required": ["public_redistribution"],
                            }
                        }
                    },
                    "then": {
                        "properties": {
                            "license": {"type": "string", "minLength": 1},
                            "permissions": {
                                "properties": {"export": {"const": "permitted"}},
                                "required": ["export"],
                            },
                            "rights_status": {"const": "verified_open"},
                        }
                    },
                },
                {
                    "if": {
                        "properties": {"rights_status": {"const": "analysis_only"}},
                        "required": ["rights_status"],
                    },
                    "then": {
                        "properties": {
                            "permissions": {
                                "properties": {
                                    "analysis": {"const": "permitted"},
                                    "export": {"const": "prohibited"},
                                    "public_redistribution": {"const": "prohibited"},
                                    "upload": {"const": "permitted"},
                                }
                            }
                        }
                    },
                },
                {
                    "if": {
                        "properties": {"rights_status": {"const": "excluded"}},
                        "required": ["rights_status"],
                    },
                    "then": {
                        "properties": {
                            "permissions": {
                                "properties": {
                                    "analysis": {"const": "prohibited"},
                                    "export": {"const": "prohibited"},
                                    "public_redistribution": {"const": "prohibited"},
                                    "upload": {"const": "prohibited"},
                                }
                            }
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "permissions": {
                                "anyOf": [
                                    {
                                        "properties": {"upload": {"const": "permitted"}},
                                        "required": ["upload"],
                                    },
                                    {
                                        "properties": {"analysis": {"const": "permitted"}},
                                        "required": ["analysis"],
                                    },
                                    {
                                        "properties": {"export": {"const": "permitted"}},
                                        "required": ["export"],
                                    },
                                    {
                                        "properties": {
                                            "public_redistribution": {"const": "permitted"}
                                        },
                                        "required": ["public_redistribution"],
                                    },
                                ]
                            }
                        },
                        "required": ["permissions"],
                    },
                    "then": {
                        "properties": {"evidence": {"minItems": 1}},
                        "required": ["evidence"],
                    },
                },
                {
                    "if": {
                        "properties": {"rights_status": {"const": "verified_open"}},
                        "required": ["rights_status"],
                    },
                    "then": {
                        "properties": {
                            "evidence": {"minItems": 1},
                            "license": {"type": "string", "minLength": 1},
                        },
                        "required": ["evidence", "license"],
                    },
                },
            ]
        },
    )

    schema_version: Literal["2.0.0"] = "2.0.0"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    source_id: str = Field(pattern=SLUG_PATTERN)
    asset_type: AssetType
    rights_status: RightsStatus
    license: str | None = Field(default=None, min_length=1)
    permissions: ActionPermissions
    evidence: tuple[RightsEvidence, ...] = ()
    jurisdiction: str | None = Field(default=None, min_length=1)
    assessed_by: str = Field(min_length=1)
    assessed_at_utc: datetime = Field(json_schema_extra={"pattern": r"(?:Z|[+-]00:00)$"})
    notes: str = ""

    @model_validator(mode="after")
    def require_coherent_rights(self) -> Self:
        if self.assessed_at_utc.utcoffset() != timedelta(0):
            raise ValueError("rights assessment timestamps must be UTC")
        states = tuple(self.permissions.model_dump().values())
        if PermissionState.PERMITTED in states and not self.evidence:
            raise ValueError("permitted actions require rights evidence")
        if self.rights_status is RightsStatus.VERIFIED_OPEN and (
            not self.license or not self.evidence
        ):
            raise ValueError("verified-open rights require a license and evidence")
        if self.permissions.public_redistribution is PermissionState.PERMITTED and (
            self.rights_status is not RightsStatus.VERIFIED_OPEN
            or self.permissions.export is not PermissionState.PERMITTED
            or not self.license
        ):
            raise ValueError("public redistribution requires verified-open export rights")
        if self.rights_status is RightsStatus.ANALYSIS_ONLY:
            expected = (
                PermissionState.PERMITTED,
                PermissionState.PERMITTED,
                PermissionState.PROHIBITED,
                PermissionState.PROHIBITED,
            )
            if states != expected:
                raise ValueError("analysis-only rights require the analysis-only profile")
        if self.rights_status is RightsStatus.EXCLUDED and any(
            state is not PermissionState.PROHIBITED for state in states
        ):
            raise ValueError("excluded assets must prohibit every action")
        return self

    @property
    def allows_analysis(self) -> bool:
        return (
            self.permissions.upload is PermissionState.PERMITTED
            and self.permissions.analysis is PermissionState.PERMITTED
        )

    @property
    def allows_public_redistribution(self) -> bool:
        return (
            self.rights_status is RightsStatus.VERIFIED_OPEN
            and self.permissions.export is PermissionState.PERMITTED
            and self.permissions.public_redistribution is PermissionState.PERMITTED
            and self.license is not None
        )


__all__ = [
    "ActionPermissions",
    "AssetRightsRecord",
    "AssetType",
    "PermissionState",
    "RightsEvidence",
    "RightsStatus",
]
