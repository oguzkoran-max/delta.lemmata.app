from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_generated_evidence.py"
NORMALIZER = ROOT / "scripts" / "normalize_python_sbom.py"
EXPECTED_FILES = (
    "checksums.sha256",
    "detect-secrets.json",
    "pip-audit.json",
    "python-environment.txt",
    "python-sbom.cdx.json",
    "r-sbom.cdx.json",
    "r-session-info.txt",
    "runtime-requirements.txt",
)
SOURCE_PATHS = (
    "VERSION",
    "uv.lock",
    "renv.lock",
    "CITATION.cff",
    "codemeta.json",
    "containers/base-images.lock.json",
    "containers/ci-actions.lock.json",
)


def make_package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    package.mkdir()
    checksums = "".join(f"{'a' * 64}  {path}\n" for path in SOURCE_PATHS)
    payloads = {
        "checksums.sha256": checksums,
        "detect-secrets.json": json.dumps({"results": {}}),
        "pip-audit.json": json.dumps({"dependencies": []}),
        "python-environment.txt": "jsonschema==4.26.0\n",
        "python-sbom.cdx.json": json.dumps({"bomFormat": "CycloneDX"}),
        "r-sbom.cdx.json": json.dumps({"bomFormat": "CycloneDX"}),
        "r-session-info.txt": "R version 4.5.2\n",
        "runtime-requirements.txt": "jsonschema==4.26.0 --hash=sha256:abc\n",
    }
    for name, payload in payloads.items():
        (package / name).write_text(payload, encoding="utf-8")
    return package


def run_validator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def run_normalizer(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(NORMALIZER), str(path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_valid_package_writes_and_verifies_manifest(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    manifest = tmp_path / "package.sha256"

    written = run_validator(str(package), "--write-manifest", str(manifest))
    verified = run_validator(str(package), "--manifest", str(manifest))

    assert written.returncode == 0
    assert verified.returncode == 0
    assert written.stdout == f"evidence-package-ok path={package}\n"
    lines = manifest.read_text(encoding="utf-8").splitlines()
    assert [line.split("  ", maxsplit=1)[1] for line in lines] == list(EXPECTED_FILES)
    for line in lines:
        digest, name = line.split("  ", maxsplit=1)
        expected = hashlib.sha256((package / name).read_bytes()).hexdigest()
        assert digest == expected


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing", "inventory mismatch"),
        ("extra", "inventory mismatch"),
        ("empty", "empty evidence file"),
        ("binary", "not UTF-8"),
        ("nul", "NUL byte"),
        ("private", "private path marker"),
        ("windows", "private Windows user path"),
        ("json", "invalid JSON"),
        ("json-root", "JSON root is not an object"),
        ("checksum-line", "invalid source checksum line"),
        ("checksum-order", "source checksum inventory mismatch"),
    ],
)
def test_invalid_package_is_rejected(tmp_path: Path, mutation: str, message: str) -> None:
    package = make_package(tmp_path)
    if mutation == "missing":
        (package / "r-session-info.txt").unlink()
    elif mutation == "extra":
        (package / "extra.txt").write_text("extra", encoding="utf-8")
    elif mutation == "empty":
        (package / "r-session-info.txt").write_text("", encoding="utf-8")
    elif mutation == "binary":
        (package / "r-session-info.txt").write_bytes(b"\xff")
    elif mutation == "nul":
        (package / "r-session-info.txt").write_bytes(b"R\x00")
    elif mutation == "private":
        (package / "r-session-info.txt").write_text("file:///tmp/private", encoding="utf-8")
    elif mutation == "windows":
        (package / "r-session-info.txt").write_text(r"C:\\Users\\Researcher\\run", encoding="utf-8")
    elif mutation == "json":
        (package / "pip-audit.json").write_text("{", encoding="utf-8")
    elif mutation == "json-root":
        (package / "pip-audit.json").write_text("[]", encoding="utf-8")
    elif mutation == "checksum-line":
        (package / "checksums.sha256").write_text("wrong", encoding="utf-8")
    else:
        lines = (package / "checksums.sha256").read_text(encoding="utf-8").splitlines()
        (package / "checksums.sha256").write_text(
            "\n".join(reversed(lines)) + "\n", encoding="utf-8"
        )

    result = run_validator(str(package))

    assert result.returncode == 1
    assert message in result.stderr


def test_symlink_and_missing_directory_are_rejected(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    target = package / "r-session-info.txt"
    target.unlink()
    target.symlink_to(package / "python-environment.txt")

    symlink = run_validator(str(package))
    missing = run_validator(str(tmp_path / "missing"))

    assert symlink.returncode == 1
    assert "not a regular file" in symlink.stderr
    assert missing.returncode == 1
    assert "directory is missing" in missing.stderr


def test_manifest_mismatch_and_unsafe_manifest_are_rejected(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    manifest = tmp_path / "package.sha256"
    manifest.write_text("wrong\n", encoding="utf-8")

    mismatch = run_validator(str(package), "--manifest", str(manifest))
    manifest.unlink()
    manifest.symlink_to(package / "python-environment.txt")
    unsafe = run_validator(str(package), "--manifest", str(manifest))

    assert mismatch.returncode == 1
    assert "manifest mismatch" in mismatch.stderr
    assert unsafe.returncode == 1
    assert "manifest is missing or unsafe" in unsafe.stderr


def test_generation_and_ci_use_path_neutral_validated_evidence() -> None:
    generator = (ROOT / "scripts" / "generate_evidence.sh").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "cyclonedx-py environment" in generator
    assert "normalize_python_sbom.py" in generator
    assert "pip freeze --exclude-editable" in generator
    assert "validate_generated_evidence.py" in generator
    assert "upload-artifact" not in workflow


def test_python_sbom_normalizer_removes_only_local_file_references(tmp_path: Path) -> None:
    sbom = tmp_path / "python-sbom.cdx.json"
    sbom.write_text(
        json.dumps(
            {
                "components": [
                    {
                        "name": "delta-lemmata",
                        "externalReferences": [
                            {
                                "type": "distribution",
                                "url": "file:///" + "Users/private/project",
                            },
                            {"type": "website", "url": "https://delta.lemmata.app"},
                        ],
                    },
                    {"name": "dependency"},
                ],
                "dependencies": [{"ref": "delta-lemmata", "dependsOn": ["dependency"]}],
            }
        ),
        encoding="utf-8",
    )

    result = run_normalizer(sbom)
    loaded = json.loads(sbom.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert "removed_local_references=1" in result.stdout
    assert loaded["components"][0]["externalReferences"] == [
        {"type": "website", "url": "https://delta.lemmata.app"}
    ]
    assert loaded["dependencies"] == [{"dependsOn": ["dependency"], "ref": "delta-lemmata"}]


@pytest.mark.parametrize(
    "payload",
    ["[]", '{"components": {}}', '{"components": [null]}'],
)
def test_python_sbom_normalizer_rejects_invalid_structure(tmp_path: Path, payload: str) -> None:
    sbom = tmp_path / "python-sbom.cdx.json"
    sbom.write_text(payload, encoding="utf-8")

    result = run_normalizer(sbom)

    assert result.returncode == 1
    assert "python-sbom-normalization-error" in result.stderr
