"""Canonical P004 corpus inventory and semantic identity helpers."""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import Field

from delta_lemmata.corpus_models import (
    SHA256_PATTERN,
    AssetRecord,
    AuthorRecord,
    EditionRecord,
    FrozenModel,
    PurposeId,
    SourceRecord,
    ValidatedFileRecord,
    WorkRecord,
)
from delta_lemmata.provenance import canonical_json_bytes
from delta_lemmata.rights import AssetRightsRecord


class CorpusInventory(FrozenModel):
    schema_version: Literal["corpus-inventory-v1"] = "corpus-inventory-v1"
    vocabulary_profile: Literal["corpus-vocabularies-v1"] = "corpus-vocabularies-v1"
    purpose: PurposeId
    authors: tuple[AuthorRecord, ...] = Field(min_length=1)
    works: tuple[WorkRecord, ...] = Field(min_length=1)
    editions: tuple[EditionRecord, ...] = Field(min_length=1)
    sources: tuple[SourceRecord, ...] = Field(min_length=1)
    assets: tuple[AssetRecord, ...] = Field(min_length=1)
    validated_files: tuple[ValidatedFileRecord, ...] = Field(min_length=1)
    rights: tuple[AssetRightsRecord, ...] = Field(min_length=1)


class InventoryBinding(FrozenModel):
    """The inventory identity to which a downstream run is bound."""

    schema_version: Literal["inventory-binding-v1"] = "inventory-binding-v1"
    inventory_sha256: str = Field(pattern=SHA256_PATTERN)

    def matches(self, inventory: CorpusInventory) -> bool:
        return self.inventory_sha256 == inventory_sha256(inventory)


def _authority_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (record["scheme"], record["value"], record.get("url") or "")


def _contributor_key(record: dict[str, Any]) -> tuple[str, str]:
    return (record["author_id"], record["role"])


def _evidence_key(record: dict[str, Any]) -> tuple[str, str]:
    return (record["evidence_type"], record["value"])


def _payload_key(record: dict[str, Any], id_field: str) -> tuple[str, bytes]:
    return (record[id_field], canonical_json_bytes(record))


def canonical_inventory_payload(inventory: CorpusInventory) -> dict[str, Any]:
    """Project an inventory to upload-order-invariant semantic JSON.

    The rights assessment timestamp is audit provenance rather than analysis input,
    so changing only that volatile timestamp does not invalidate a downstream run.
    """

    authors = []
    for author in inventory.authors:
        record = author.model_dump(mode="json")
        record["authority_identifiers"] = sorted(
            record["authority_identifiers"], key=_authority_key
        )
        authors.append(record)
    authors.sort(key=lambda record: _payload_key(record, "author_id"))

    works = []
    for work in inventory.works:
        record = work.model_dump(mode="json")
        record["contributors"] = sorted(record["contributors"], key=_contributor_key)
        works.append(record)
    works.sort(key=lambda record: _payload_key(record, "work_id"))

    rights_records = []
    for rights in inventory.rights:
        record = rights.model_dump(mode="json", exclude={"assessed_at_utc"})
        record["evidence"] = sorted(record["evidence"], key=_evidence_key)
        rights_records.append(record)
    rights_records.sort(key=lambda record: _payload_key(record, "asset_id"))

    editions = [record.model_dump(mode="json") for record in inventory.editions]
    editions.sort(key=lambda record: _payload_key(record, "edition_id"))
    sources = [record.model_dump(mode="json") for record in inventory.sources]
    sources.sort(key=lambda record: _payload_key(record, "source_id"))
    assets = []
    for asset in inventory.assets:
        record = asset.model_dump(mode="json")
        record["rights_asset_ids"] = sorted(record["rights_asset_ids"])
        assets.append(record)
    assets.sort(key=lambda record: _payload_key(record, "asset_id"))
    validated_files = [record.model_dump(mode="json") for record in inventory.validated_files]
    validated_files.sort(key=lambda record: _payload_key(record, "file_label"))

    return {
        "schema_version": inventory.schema_version,
        "vocabulary_profile": inventory.vocabulary_profile,
        "purpose": inventory.purpose.value,
        "authors": authors,
        "works": works,
        "editions": editions,
        "sources": sources,
        "assets": assets,
        "validated_files": validated_files,
        "rights": rights_records,
    }


def inventory_sha256(inventory: CorpusInventory) -> str:
    return hashlib.sha256(canonical_json_bytes(canonical_inventory_payload(inventory))).hexdigest()


def bind_inventory(inventory: CorpusInventory) -> InventoryBinding:
    return InventoryBinding(inventory_sha256=inventory_sha256(inventory))


def asset_allows_public_redistribution(
    asset: AssetRecord,
    rights_records: tuple[AssetRightsRecord, ...],
) -> bool:
    """Fail closed unless every declared rights layer permits public export."""

    rights_by_asset = {rights.asset_id: rights for rights in rights_records}
    if (
        not asset.rights_chain_confirmed
        or asset.asset_id not in asset.rights_asset_ids
        or len(rights_by_asset) != len(rights_records)
    ):
        return False
    return all(
        (rights := rights_by_asset.get(rights_id)) is not None
        and rights.allows_public_redistribution
        for rights_id in asset.rights_asset_ids
    )


__all__ = [
    "CorpusInventory",
    "InventoryBinding",
    "asset_allows_public_redistribution",
    "bind_inventory",
    "canonical_inventory_payload",
    "inventory_sha256",
]
