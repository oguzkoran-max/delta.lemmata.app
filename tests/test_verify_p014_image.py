from __future__ import annotations

import importlib.util
import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "verify_p014_image.py"
SOURCE_SHA = "a" * 40
IMAGE_REFERENCE = f"ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:{'b' * 64}"
IMAGE_ID = f"sha256:{'c' * 64}"


def _load_script():
    spec = importlib.util.spec_from_file_location("verify_p014_image", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFIER = _load_script()


def _metadata() -> dict[str, object]:
    return {
        "Id": IMAGE_ID,
        "RepoDigests": [IMAGE_REFERENCE],
        "Config": {
            "Labels": {
                "org.opencontainers.image.revision": SOURCE_SHA,
                "org.opencontainers.image.source": (
                    "https://github.com/oguzkoran-max/delta.lemmata.app"
                ),
            }
        },
    }


def test_image_metadata_binds_digest_and_revision() -> None:
    assert (
        VERIFIER.verify_image_metadata(
            _metadata(), image_reference=IMAGE_REFERENCE, source_sha=SOURCE_SHA
        )
        == IMAGE_ID
    )


def test_image_metadata_rejects_digest_mismatch() -> None:
    metadata = _metadata()
    metadata["RepoDigests"] = [f"ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:{'d' * 64}"]
    with pytest.raises(VERIFIER.ImageVerificationError, match="P014_IMAGE_DIGEST_MISMATCH"):
        VERIFIER.verify_image_metadata(
            metadata, image_reference=IMAGE_REFERENCE, source_sha=SOURCE_SHA
        )


def test_image_metadata_rejects_revision_mismatch() -> None:
    metadata = _metadata()
    metadata["Config"]["Labels"]["org.opencontainers.image.revision"] = "e" * 40
    with pytest.raises(VERIFIER.ImageVerificationError, match="P014_IMAGE_REVISION_MISMATCH"):
        VERIFIER.verify_image_metadata(
            metadata, image_reference=IMAGE_REFERENCE, source_sha=SOURCE_SHA
        )


@pytest.mark.parametrize(
    ("image_reference", "source_sha", "code"),
    [
        ("ghcr.io/example/delta:latest", SOURCE_SHA, "P014_IMAGE_REFERENCE_NOT_IMMUTABLE"),
        (IMAGE_REFERENCE, "ABC", "P014_IMAGE_SOURCE_SHA_INVALID"),
    ],
)
def test_image_verifier_rejects_mutable_or_malformed_inputs(
    image_reference: str, source_sha: str, code: str
) -> None:
    with pytest.raises(VERIFIER.ImageVerificationError, match=code):
        VERIFIER.validate_inputs(image_reference, source_sha)


def test_cli_fails_closed_when_docker_reports_wrong_revision(tmp_path: Path) -> None:
    metadata = _metadata()
    metadata["Config"]["Labels"]["org.opencontainers.image.revision"] = "f" * 40
    fake_docker = tmp_path / "docker"
    fake_docker.write_text(
        "#!/bin/sh\nprintf '%s\\n' '" + json.dumps([metadata]) + "'\n",
        encoding="utf-8",
    )
    fake_docker.chmod(fake_docker.stat().st_mode | stat.S_IXUSR)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--image-reference",
            IMAGE_REFERENCE,
            "--source-sha",
            SOURCE_SHA,
            "--docker-binary",
            str(fake_docker),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr == "P014_IMAGE_REVISION_MISMATCH\n"
