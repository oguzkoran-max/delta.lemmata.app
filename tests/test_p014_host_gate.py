from __future__ import annotations

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "scripts" / "p014_host_gate.py"
INSTALL_PATH = ROOT / "scripts" / "p014_install_docker_ubuntu.sh"
ROLLBACK_PATH = ROOT / "scripts" / "p014_rollback_docker_ubuntu.sh"
RUNBOOK_PATH = ROOT / "deploy" / "public-alpha" / "README.md"


def _load_gate():
    spec = importlib.util.spec_from_file_location("p014_host_gate", GATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _health(p95: float = 100.0, *, samples: int = 20) -> dict[str, Any]:
    return {
        "samples": samples,
        "successes": samples,
        "body_ok": samples,
        "median_ms": min(80.0, p95),
        "p95_ms": p95,
        "max_ms": p95,
    }


def _firewall() -> dict[str, Any]:
    return {
        "nftables": {"line_count": 0, "sha256": "1" * 64},
        "iptables": {"line_count": 0, "sha256": "2" * 64},
        "ip6tables": {"line_count": 0, "sha256": "3" * 64},
    }


def _baseline() -> dict[str, Any]:
    return {
        "schema_version": "1.3.0",
        "capture_mode": "live",
        "phase": "pre-docker",
        "captured_at_utc": "2026-07-15T18:30:00Z",
        "host": {
            "identity": {
                "machine_id_sha256": "4" * 64,
                "boot_id_sha256": "5" * 64,
                "kernel_release": "6.17.0-4-generic",
            },
            "os": {"ID": "ubuntu", "VERSION_ID": "26.04", "VERSION_CODENAME": "resolute"},
            "architecture": "x86_64",
            "cpu_count": 2,
            "memory": {"total_mib": 3814, "available_mib": 2357, "swap_total_mib": 0},
            "root_free_mib": 32621,
            "memory_pressure": {"some_avg10": 0.0, "full_avg10": 0.0},
            "forwarding": {"ipv4": 0, "ipv6": 0},
            "firewall": _firewall(),
            "listeners": [
                {"address": "0.0.0.0", "port": 22},
                {"address": "0.0.0.0", "port": 80},
                {"address": "0.0.0.0", "port": 443},
                {"address": "127.0.0.1", "port": 8501},
            ],
            "kernel_oom_markers_30m": 0,
        },
        "services": {
            "caddy": "active",
            "lemmata": "active",
            "docker": "inactive",
            "delta_public_alpha": "inactive",
        },
        "lemmata": {
            "service": {
                "active_state": "active",
                "sub_state": "running",
                "restart_count": 0,
                "memory_bytes": 1118232576,
                "start_monotonic_us": 100,
            },
            "health": _health(),
        },
        "delta": {"health": None},
        "caddyfile_sha256": "6" * 64,
        "docker": {
            "installed": False,
            "service": "inactive",
            "engine_version": None,
            "compose_version": None,
            "packages": {},
            "candidate_versions": {},
            "official_candidates": {},
            "repository": {
                "key_sha256": None,
                "source_sha256": None,
                "primary_fingerprints": [],
                "source_profile_valid": False,
            },
        },
        "gate": {"passed": True, "failures": []},
    }


def _post_docker() -> dict[str, Any]:
    value = copy.deepcopy(_baseline())
    value["phase"] = "post-docker"
    value["captured_at_utc"] = "2026-07-15T18:31:00Z"
    value["host"]["memory"]["available_mib"] = 2200
    value["host"]["forwarding"] = {"ipv4": 1, "ipv6": 1}
    value["host"]["firewall"]["nftables"] = {"line_count": 40, "sha256": "7" * 64}
    value["services"]["docker"] = "active"
    value["docker"].update(
        {
            "installed": True,
            "service": "active",
            "engine_version": "29.1.0",
            "compose_version": "5.0.0",
            "packages": {
                package: f"1.0-{index}" for index, package in enumerate(GATE.DOCKER_PACKAGES)
            },
            "candidate_versions": {
                package: f"1.0-{index}" for index, package in enumerate(GATE.DOCKER_PACKAGES)
            },
            "official_candidates": {package: True for package in GATE.DOCKER_PACKAGES},
            "repository": {
                "key_sha256": "8" * 64,
                "source_sha256": "9" * 64,
                "primary_fingerprints": [GATE.EXPECTED_DOCKER_KEY_FINGERPRINT],
                "source_profile_valid": True,
            },
        }
    )
    value["lemmata"]["health"] = _health(110.0)
    value.pop("gate")
    return value


def _delta() -> dict[str, Any]:
    value = _post_docker()
    value["phase"] = "delta-idle"
    value["captured_at_utc"] = "2026-07-15T18:32:00Z"
    value["host"]["memory"]["available_mib"] = 900
    value["host"]["listeners"].append({"address": "127.0.0.1", "port": 8502})
    value["services"]["delta_public_alpha"] = "active"
    value["delta"]["health"] = _health(15.0)
    return value


def _post_rollback() -> dict[str, Any]:
    value = copy.deepcopy(_baseline())
    value["phase"] = "post-rollback"
    value["captured_at_utc"] = "2026-07-15T18:33:00Z"
    value.pop("gate")
    return value


def test_pre_docker_snapshot_passes_the_frozen_gate() -> None:
    assert GATE.evaluate_snapshot(_baseline(), None) == []


def test_post_docker_snapshot_passes_only_with_exact_profile_and_socket_set() -> None:
    assert GATE.evaluate_snapshot(_post_docker(), _baseline()) == []
    value = _post_docker()
    value["docker"]["packages"].pop("docker-compose-plugin")
    value["docker"]["repository"]["key_sha256"] = None
    failures = GATE.evaluate_snapshot(value, _baseline())
    assert "P014_DOCKER_PACKAGE_SET_INVALID" in failures
    assert "P014_DOCKER_CANDIDATE_VERSION_MISMATCH" in failures
    assert "P014_DOCKER_REPOSITORY_EVIDENCE_MISSING" in failures


def test_post_docker_rejects_wrong_candidate_origin_key_and_source_profile() -> None:
    value = _post_docker()
    value["docker"]["candidate_versions"]["docker-ce"] = "forged-version"
    value["docker"]["official_candidates"]["docker-compose-plugin"] = False
    value["docker"]["repository"]["primary_fingerprints"] = ["A" * 40]
    value["docker"]["repository"]["source_profile_valid"] = False
    failures = GATE.evaluate_snapshot(value, _baseline())
    assert "P014_DOCKER_CANDIDATE_VERSION_MISMATCH" in failures
    assert "P014_DOCKER_PACKAGE_ORIGIN_INVALID" in failures
    assert "P014_DOCKER_REPOSITORY_EVIDENCE_MISSING" in failures


def test_post_docker_rejects_an_extra_primary_signing_key() -> None:
    value = _post_docker()
    value["docker"]["repository"]["primary_fingerprints"].append("A" * 40)
    assert "P014_DOCKER_REPOSITORY_EVIDENCE_MISSING" in GATE.evaluate_snapshot(value, _baseline())


def test_pre_mutation_rechecks_every_change_sensitive_host_boundary() -> None:
    value = copy.deepcopy(_baseline())
    value["phase"] = "pre-mutation"
    value["captured_at_utc"] = "2026-07-15T18:31:00Z"
    value.pop("gate")
    assert GATE.evaluate_snapshot(value, _baseline()) == []

    value["host"]["listeners"].append({"address": "0.0.0.0", "port": 2375})
    value["host"]["forwarding"]["ipv4"] = 1
    value["host"]["firewall"]["nftables"]["sha256"] = "a" * 64
    value["lemmata"]["service"]["start_monotonic_us"] += 1
    failures = GATE.evaluate_snapshot(value, _baseline())
    assert "P014_LEMMATA_START_CHANGED" in failures
    assert "P014_PRE_MUTATION_LISTENERS_CHANGED" in failures
    assert "P014_PRE_MUTATION_FORWARDING_CHANGED" in failures
    assert "P014_PRE_MUTATION_FIREWALL_CHANGED" in failures


def test_apt_candidate_requires_an_isolated_exact_official_stanza(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    apt_lists_dir = Path("/root/p014-host-evidence/docker-change/apt-lists")
    official = (
        "docker-ce:\n"
        "  Installed: (none)\n"
        "  Candidate: 5:29.1.3-1~ubuntu.26.04~resolute\n"
        "  Version table:\n"
        "     5:29.1.3-1~ubuntu.26.04~resolute 500\n"
        "        500 https://download.docker.com/linux/ubuntu "
        "resolute/stable amd64 Packages\n"
    )
    hostile = official.replace(
        "https://download.docker.com/linux/ubuntu resolute/stable",
        "https://packages.invalid/ubuntu resolute/stable",
    )
    monkeypatch.setattr(
        GATE,
        "_read_os_release",
        lambda: {"ID": "ubuntu", "VERSION_ID": "26.04", "VERSION_CODENAME": "resolute"},
    )

    def policy_output(isolated: str, expected_lists_dir: Path | None):
        def fake(command: list[str], **_kwargs) -> str:
            if command[:2] == ["dpkg", "--print-architecture"]:
                return "amd64"
            assert "Dir::Etc::sourceparts=-" in command
            list_options = [token for token in command if token.startswith("Dir::State::lists=")]
            if expected_lists_dir is None:
                assert list_options == []
            else:
                assert list_options == [f"Dir::State::lists={expected_lists_dir}"]
            return isolated

        return fake

    monkeypatch.setattr(GATE, "_required_stdout", policy_output(official, apt_lists_dir))
    assert GATE._apt_candidate("docker-ce", apt_lists_dir=apt_lists_dir) == (
        "5:29.1.3-1~ubuntu.26.04~resolute",
        True,
    )

    monkeypatch.setattr(GATE, "_required_stdout", policy_output(hostile, None))
    assert GATE._apt_candidate("docker-ce")[1] is False


@pytest.mark.parametrize("phase", ["post-docker", "delta-idle"])
def test_post_install_cli_requires_an_absolute_private_apt_list_directory(phase: str) -> None:
    common = [
        phase,
        "--baseline",
        "/root/p014-host-evidence/pre-docker.json",
        "--output",
        f"/root/p014-host-evidence/{phase}.json",
    ]

    with pytest.raises(SystemExit, match="2"):
        GATE._parse_args(common)
    with pytest.raises(SystemExit, match="2"):
        GATE._parse_args([*common, "--apt-lists-dir", "relative/apt-lists"])

    args = GATE._parse_args(
        [
            *common,
            "--apt-lists-dir",
            "/root/p014-host-evidence/docker-change/apt-lists",
        ]
    )
    assert args.apt_lists_dir == Path("/root/p014-host-evidence/docker-change/apt-lists")


def test_pre_docker_cli_rejects_an_apt_list_directory() -> None:
    with pytest.raises(SystemExit, match="2"):
        GATE._parse_args(
            [
                "pre-docker",
                "--output",
                "/root/p014-host-evidence/pre-docker.json",
                "--apt-lists-dir",
                "/root/p014-host-evidence/docker-change/apt-lists",
            ]
        )


def test_docker_key_evidence_retains_every_primary_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = tmp_path / "docker.asc"
    key.write_text("placeholder", encoding="ascii")
    monkeypatch.setattr(GATE, "DOCKER_KEY", key)
    monkeypatch.setattr(
        GATE,
        "_required_stdout",
        lambda _command: "\n".join(
            (
                "pub:-:4096:1:1111111111111111:0:0::::::scESC::::::23::0:",
                f"fpr:::::::::{GATE.EXPECTED_DOCKER_KEY_FINGERPRINT}:",
                "uid:-::::0::0::Docker Release::::::::::0:",
                "sub:-:4096:1:2222222222222222:0:0::::::e::::::23:",
                f"fpr:::::::::{'B' * 40}:",
                "pub:-:4096:1:3333333333333333:0:0::::::scESC::::::23::0:",
                f"fpr:::::::::{'A' * 40}:",
            )
        ),
    )
    assert GATE._docker_primary_fingerprints() == [
        GATE.EXPECTED_DOCKER_KEY_FINGERPRINT,
        "A" * 40,
    ]


def test_post_docker_gate_rejects_latency_memory_and_listener_regressions() -> None:
    value = _post_docker()
    value["lemmata"]["health"] = _health(120.001)
    value["host"]["memory"]["available_mib"] = 1799
    value["host"]["listeners"].append({"address": "0.0.0.0", "port": 2375})
    failures = GATE.evaluate_snapshot(value, _baseline())
    assert failures[-3:] == [
        "P014_LEMMATA_P95_BUDGET_EXCEEDED",
        "P014_POST_DOCKER_MEMORY_LOW",
        "P014_UNEXPECTED_LISTENER_AFTER_DOCKER",
    ]


def test_delta_idle_requires_exactly_one_new_loopback_listener() -> None:
    assert GATE.evaluate_snapshot(_delta(), _baseline()) == []
    value = _delta()
    value["host"]["listeners"].append({"address": "0.0.0.0", "port": 5000})
    assert "P014_DELTA_LISTENER_SET_INVALID" in GATE.evaluate_snapshot(value, _baseline())
    value = _delta()
    value["host"]["listeners"][-1] = {"address": "0.0.0.0", "port": 8502}
    value["host"]["memory_pressure"]["full_avg10"] = 1.0
    assert GATE.evaluate_snapshot(value, _baseline())[-2:] == [
        "P014_DELTA_LISTENER_SET_INVALID",
        "P014_MEMORY_PRESSURE_HIGH",
    ]


def test_post_rollback_requires_the_original_network_and_runtime_absence() -> None:
    value = _post_rollback()
    assert GATE.evaluate_snapshot(value, _baseline()) == []
    value["host"]["forwarding"]["ipv4"] = 1
    value["host"]["firewall"]["nftables"]["sha256"] = "a" * 64
    value["docker"]["installed"] = True
    assert GATE.evaluate_snapshot(value, _baseline())[-3:] == [
        "P014_DOCKER_ROLLBACK_INCOMPLETE",
        "P014_FORWARDING_NOT_RESTORED",
        "P014_FIREWALL_NOT_RESTORED",
    ]


def test_profile_swap_and_oom_requirements_apply_after_installation() -> None:
    value = _post_docker()
    value["host"]["os"]["VERSION_ID"] = "24.04"
    value["host"]["cpu_count"] = 1
    value["host"]["memory"]["swap_total_mib"] = 1024
    value["host"]["kernel_oom_markers_30m"] = 1
    assert GATE.evaluate_snapshot(value, _baseline())[:3] == [
        "P014_HOST_PROFILE_UNSUPPORTED",
        "P014_UNEXPECTED_HOST_SWAP",
        "P014_KERNEL_OOM_OBSERVED",
    ]


def test_baseline_must_be_fresh_and_from_the_same_host_and_boot() -> None:
    value = _post_docker()
    value["captured_at_utc"] = "2026-07-15T21:00:01Z"
    value["host"]["identity"]["boot_id_sha256"] = "b" * 64
    failures = GATE.evaluate_snapshot(value, _baseline())
    assert "P014_BASELINE_HOST_OR_BOOT_CHANGED" in failures
    assert "P014_BASELINE_STALE" in failures


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value.update({"capture_mode": "test-fixture"}),
        lambda value: value.update({"unexpected_payload": "not content free"}),
        lambda value: value["lemmata"]["health"].update(
            {"samples": 0, "successes": 0, "body_ok": 0}
        ),
        lambda value: value["lemmata"]["health"].update({"p95_ms": float("nan")}),
        lambda value: value["host"]["firewall"]["nftables"].update({"sha256": None}),
    ],
)
def test_closed_schema_rejects_fixture_unknown_zero_nan_and_unknown_telemetry(mutator) -> None:
    value = _baseline()
    mutator(value)
    assert GATE.evaluate_snapshot(value, None) == ["P014_SNAPSHOT_INVALID"]


def test_json_loader_rejects_non_finite_constants(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"value": NaN}', encoding="utf-8")
    with pytest.raises(GATE.HostGateError, match="P014_JSON_CONSTANT_INVALID"):
        GATE._load_json(path)


def test_production_cli_has_no_snapshot_or_under_load_fixture_channel() -> None:
    completed = subprocess.run(
        [sys.executable, str(GATE_PATH), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "--snapshot" not in completed.stdout
    assert "under-load" not in completed.stdout
    rejected = subprocess.run(
        [
            sys.executable,
            str(GATE_PATH),
            "pre-docker",
            "--output",
            "/tmp/evidence.json",
            "--snapshot",
            "/tmp/fixture.json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode == 2
    assert "unrecognized arguments: --snapshot" in rejected.stderr


def test_host_change_scripts_are_guarded_exact_and_syntactically_valid() -> None:
    for path in (INSTALL_PATH, ROLLBACK_PATH):
        completed = subprocess.run(
            ["bash", "-n", str(path)], check=False, capture_output=True, text=True
        )
        assert completed.returncode == 0, completed.stderr
    install = INSTALL_PATH.read_text(encoding="utf-8")
    rollback = ROLLBACK_PATH.read_text(encoding="utf-8")
    assert "--apply" in install and "--apply" in rollback
    assert "https://download.docker.com/linux/ubuntu/gpg" in install
    assert "9DC858229FC7DD38854AE2D88D81803C0EBFCD88" in install
    assert 'SPECS+=("$package=$candidate")' in install
    assert "--no-install-recommends" in install
    assert '"$ROLLBACK" --state-dir' in install
    assert "rollback-armed" in install + rollback
    assert "install-complete" in install + rollback
    for conflict in ("docker-compose", "docker-compose-v2", "docker-doc"):
        assert conflict in install
    assert "PACKAGE_ALLOWLIST" in rollback
    assert "post-rollback" in rollback
    assert "systemctl restart lemmata" not in install + rollback
    assert "systemctl stop lemmata" not in install + rollback


def test_runbook_orders_publication_host_gates_and_separate_route_authorization() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    headings = (
        "## Phase 0: Publish the Exact Application Image",
        "## Phase 1: Read-Only Host Inventory",
        "## Phase 2: Accept Runtime and Capacity Policy",
        "## Phase 3: Install and Compare the Container Runtime",
        "## Phase 4: Install an Immutable Release",
        "## Phase 5: Obtain Separate Pre-Caddy Owner Authorization",
        "## Phase 6: Add the Delta-Only TLS Route",
        "## Phase 7: Coexistence and Load Gate",
        "## Rollback",
        "## Activation Decision",
    )
    assert [runbook.index(heading) for heading in headings] == sorted(
        runbook.index(heading) for heading in headings
    )
    assert "p014_install_docker_ubuntu.sh" in runbook
    assert "p014_rollback_docker_ubuntu.sh" in runbook
    assert "p014_host_gate.py pre-docker" in runbook
    phase_3 = runbook[
        runbook.index("## Phase 3: Install and Compare the Container Runtime") : runbook.index(
            "## Phase 4: Install an Immutable Release"
        )
    ]
    assert "--preflight /root/p014-host-evidence/pre-docker.json" in phase_3
    assert "p014_host_gate.py pre-mutation" not in phase_3
    assert "--preflight /root/p014-host-evidence/pre-mutation.json" not in phase_3
    assert "p014_host_gate.py post-docker" not in runbook
    assert "p014_host_gate.py delta-idle" in runbook
    assert "p014_host_gate.py under-load" not in runbook
    assert "p014_load_gate.py" in runbook
    assert "DOCKER_CONFIG=" in runbook
    assert "docker logout ghcr.io" in runbook
    assert "inspect_p014_runtime.py" in runbook
    assert "systemctl stop delta-public-alpha.service" in runbook
    assert "systemctl disable delta-public-alpha.service" in runbook
    assert "docker compose" in runbook and "down" in runbook
    assert "Caddyfile.pre-delta" in runbook
    assert "systemctl reload caddy" in runbook
