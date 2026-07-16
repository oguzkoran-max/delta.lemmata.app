#!/usr/bin/env python3
"""Verify that a locally pulled P014 image matches its immutable release evidence."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from typing import Any

IMAGE_REFERENCE_PATTERN = re.compile(
    r"^(?P<repository>[a-z0-9][a-z0-9._/-]*)@sha256:(?P<digest>[0-9a-f]{64})$"
)
SOURCE_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
REVISION_LABEL = "org.opencontainers.image.revision"


class ImageVerificationError(RuntimeError):
    """A deterministic immutable-image verification failure."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ImageVerificationError(code)


def validate_inputs(image_reference: str, source_sha: str) -> None:
    _require(
        IMAGE_REFERENCE_PATTERN.fullmatch(image_reference) is not None,
        "P014_IMAGE_REFERENCE_NOT_IMMUTABLE",
    )
    _require(
        SOURCE_SHA_PATTERN.fullmatch(source_sha) is not None,
        "P014_IMAGE_SOURCE_SHA_INVALID",
    )


def verify_image_metadata(
    metadata: Any,
    *,
    image_reference: str,
    source_sha: str,
) -> str:
    """Validate Docker inspect metadata and return the content-addressed image ID."""
    validate_inputs(image_reference, source_sha)
    _require(isinstance(metadata, Mapping), "P014_IMAGE_METADATA_INVALID")

    image_id = metadata.get("Id")
    _require(
        isinstance(image_id, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is not None,
        "P014_IMAGE_ID_INVALID",
    )

    repo_digests = metadata.get("RepoDigests")
    _require(
        isinstance(repo_digests, list) and all(isinstance(item, str) for item in repo_digests),
        "P014_IMAGE_REPO_DIGESTS_INVALID",
    )
    _require(image_reference in repo_digests, "P014_IMAGE_DIGEST_MISMATCH")

    config = metadata.get("Config")
    _require(isinstance(config, Mapping), "P014_IMAGE_CONFIG_INVALID")
    labels = config.get("Labels")
    _require(isinstance(labels, Mapping), "P014_IMAGE_LABELS_INVALID")
    _require(labels.get(REVISION_LABEL) == source_sha, "P014_IMAGE_REVISION_MISMATCH")
    return image_id


def inspect_local_image(image_reference: str, *, docker_binary: str = "docker") -> Any:
    try:
        completed = subprocess.run(
            [docker_binary, "image", "inspect", image_reference],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ImageVerificationError("P014_IMAGE_INSPECT_FAILED") from error
    _require(completed.returncode == 0, "P014_IMAGE_INSPECT_FAILED")
    try:
        payload = json.loads(completed.stdout, parse_constant=lambda _value: None)
    except (json.JSONDecodeError, TypeError) as error:
        raise ImageVerificationError("P014_IMAGE_INSPECT_JSON_INVALID") from error
    _require(isinstance(payload, list) and len(payload) == 1, "P014_IMAGE_INSPECT_COUNT_INVALID")
    return payload[0]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-reference", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--docker-binary", default="docker", help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        validate_inputs(arguments.image_reference, arguments.source_sha)
        metadata = inspect_local_image(
            arguments.image_reference,
            docker_binary=arguments.docker_binary,
        )
        image_id = verify_image_metadata(
            metadata,
            image_reference=arguments.image_reference,
            source_sha=arguments.source_sha,
        )
    except ImageVerificationError as error:
        print(str(error), file=__import__("sys").stderr)
        return 1
    print(f"p014-image-verification-ok image_id={image_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
