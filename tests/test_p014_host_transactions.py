from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "p014_install_docker_ubuntu.sh"
ROLLBACK = ROOT / "scripts" / "p014_rollback_docker_ubuntu.sh"
EXPECTED_FINGERPRINT = "9DC858229FC7DD38854AE2D88D81803C0EBFCD88"


def _write_executable(path: Path, payload: str) -> None:
    path.write_text(payload, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_sourced(
    script: Path,
    body: str,
    *arguments: Path | str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", 'source "$1"; shift; ' + body, "bash", str(script), *map(str, arguments)],
        cwd=ROOT,
        env={**os.environ, **(env or {})},
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_python_optimization_cannot_disable_gate_validation(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text(
        json.dumps(
            {
                "schema_version": "0.0.0",
                "capture_mode": "live",
                "phase": "pre-docker",
                "gate": {"passed": True, "failures": []},
            }
        ),
        encoding="utf-8",
    )
    invalid.chmod(0o600)

    completed = _run_sourced(
        INSTALLER,
        'validate_gate_evidence "$1" pre-docker',
        invalid,
        env={"PYTHONOPTIMIZE": "1"},
    )

    assert completed.returncode != 0
    assert "P014_DOCKER_INSTALL_GATE_" in completed.stderr
    assert "assert " not in INSTALLER.read_text(encoding="utf-8")
    assert "assert " not in ROLLBACK.read_text(encoding="utf-8")


def test_python_optimization_cannot_disable_firewall_comparison(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    baseline = evidence / "pre-docker.json"
    expected = {
        name: {"line_count": 0, "sha256": "0" * 64}
        for name in ("nftables", "iptables", "ip6tables")
    }
    baseline.write_text(json.dumps({"host": {"firewall": expected}}), encoding="utf-8")
    for name in ("nftables", "iptables", "ip6tables"):
        (evidence / f"firewall-{name}.before").write_text("changed\n", encoding="utf-8")

    completed = _run_sourced(
        INSTALLER,
        'validate_firewall_evidence "$1" "$2"',
        baseline,
        evidence,
        env={"PYTHONOPTIMIZE": "1"},
    )

    assert completed.returncode != 0
    assert "P014_DOCKER_INSTALL_FIREWALL_CAPTURE_MISMATCH" in completed.stderr


def test_python_optimization_cannot_disable_rollback_preflight_validation(
    tmp_path: Path,
) -> None:
    invalid = tmp_path / "pre-docker.json"
    invalid.write_text(
        json.dumps(
            {
                "schema_version": "0.0.0",
                "capture_mode": "live",
                "phase": "pre-docker",
                "gate": {"passed": True, "failures": []},
                "host": {"forwarding": {"ipv4": 0, "ipv6": 0}},
            }
        ),
        encoding="utf-8",
    )
    invalid.chmod(0o600)

    completed = _run_sourced(
        ROLLBACK,
        'validate_rollback_preflight "$1"',
        invalid,
        env={"PYTHONOPTIMIZE": "1"},
    )

    assert completed.returncode != 0
    assert "P014_DOCKER_ROLLBACK_PREFLIGHT_" in completed.stderr


def test_failed_docker_image_inspection_cannot_look_empty(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    evidence = tmp_path / "evidence"
    fake_bin.mkdir()
    evidence.mkdir()
    _write_executable(fake_bin / "docker", "#!/bin/sh\nexit 42\n")

    completed = _run_sourced(
        ROLLBACK,
        'inspect_docker_empty "$1"',
        evidence,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert completed.returncode != 0
    assert "P014_DOCKER_ROLLBACK_IMAGE_INSPECTION_FAILED" in completed.stderr
    assert not (evidence / "docker-runtime-inspection.txt").exists()


def test_failed_docker_container_inspection_cannot_look_empty(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    evidence = tmp_path / "evidence"
    fake_bin.mkdir()
    evidence.mkdir()
    _write_executable(
        fake_bin / "docker",
        '#!/bin/sh\nif [ "$1" = image ]; then\n  exit 0\nfi\nexit 43\n',
    )

    completed = _run_sourced(
        ROLLBACK,
        'inspect_docker_empty "$1"',
        evidence,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert completed.returncode != 0
    assert "P014_DOCKER_ROLLBACK_CONTAINER_INSPECTION_FAILED" in completed.stderr
    assert not (evidence / "docker-runtime-inspection.txt").exists()


def test_partial_install_without_docker_cli_can_continue_owned_cleanup(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()

    completed = _run_sourced(
        ROLLBACK,
        'inspect_owned_runtime_before_cleanup "$1"',
        evidence,
        env={"PATH": "/usr/bin:/bin"},
    )

    assert completed.returncode == 0, completed.stderr
    assert (evidence / "docker-runtime-inspection.txt").read_text(
        encoding="utf-8"
    ) == "partial-install-docker-cli-absent\n"


def test_inactive_partial_docker_install_does_not_require_daemon_query(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "bin"
    evidence = tmp_path / "evidence"
    fake_bin.mkdir()
    evidence.mkdir()
    _write_executable(fake_bin / "docker", "#!/bin/sh\nexit 42\n")
    _write_executable(
        fake_bin / "systemctl",
        "#!/bin/sh\n"
        'case "$2" in\n'
        "  --property=LoadState) printf 'loaded\\n'; exit 0 ;;\n"
        "  --property=ActiveState) printf 'inactive\\n'; exit 0 ;;\n"
        "esac\n"
        "exit 47\n",
    )

    completed = _run_sourced(
        ROLLBACK,
        'inspect_owned_runtime_before_cleanup "$1"',
        evidence,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert completed.returncode == 0, completed.stderr
    assert (evidence / "docker-runtime-inspection.txt").read_text(
        encoding="utf-8"
    ) == "partial-install-docker-service-inactive\n"


def test_active_docker_still_requires_successful_empty_runtime_inspection(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "bin"
    evidence = tmp_path / "evidence"
    fake_bin.mkdir()
    evidence.mkdir()
    _write_executable(fake_bin / "docker", "#!/bin/sh\nexit 42\n")
    _write_executable(
        fake_bin / "systemctl",
        "#!/bin/sh\n"
        'case "$2" in\n'
        "  --property=LoadState) printf 'loaded\\n'; exit 0 ;;\n"
        "  --property=ActiveState) printf 'active\\n'; exit 0 ;;\n"
        "esac\n"
        "exit 47\n",
    )

    completed = _run_sourced(
        ROLLBACK,
        'inspect_owned_runtime_before_cleanup "$1"',
        evidence,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert completed.returncode != 0
    assert "P014_DOCKER_ROLLBACK_IMAGE_INSPECTION_FAILED" in completed.stderr


def test_runtime_stop_failure_is_not_suppressed(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "systemctl",
        "#!/bin/sh\n"
        'if [ "$1" = show ]; then\n'
        "  printf 'loaded\\n'\n"
        "  exit 0\n"
        "fi\n"
        'if [ "$1" = stop ]; then\n'
        "  exit 44\n"
        "fi\n"
        "exit 45\n",
    )

    completed = _run_sourced(
        ROLLBACK,
        "stop_runtime_units",
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert completed.returncode != 0
    assert "P014_DOCKER_ROLLBACK_UNIT_STOP_FAILED:docker.socket" in completed.stderr


def test_failed_unit_query_cannot_be_interpreted_as_absent(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_executable(fake_bin / "systemctl", "#!/bin/sh\nexit 47\n")

    completed = _run_sourced(
        ROLLBACK,
        "runtime_units_presence",
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert completed.returncode != 0
    assert "P014_DOCKER_ROLLBACK_UNIT_LOAD_QUERY_FAILED:docker.socket" in completed.stderr


def test_runtime_must_report_inactive_after_successful_stop(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "systemctl",
        "#!/bin/sh\n"
        'case "$2" in\n'
        "  --property=LoadState) printf 'loaded\\n'; exit 0 ;;\n"
        "  --property=ActiveState) printf 'active\\n'; exit 0 ;;\n"
        "esac\n"
        'if [ "$1" = stop ]; then exit 0; fi\n'
        "exit 46\n",
    )

    completed = _run_sourced(
        ROLLBACK,
        "stop_runtime_units",
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert completed.returncode != 0
    assert "P014_DOCKER_ROLLBACK_UNIT_STILL_ACTIVE:docker.socket:active" in completed.stderr


def test_partial_owned_stage_does_not_block_safe_cleanup(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    (state / "key-owned").touch()
    final_path = tmp_path / "final-key"
    partial_stage = tmp_path / "partial-stage"
    partial_stage.write_text("partial", encoding="utf-8")
    expected = hashlib.sha256(b"expected").hexdigest()
    hash_record = state / "docker-key.sha256"
    hash_record.write_text(f"{expected}  {final_path}\n", encoding="utf-8")

    completed = _run_sourced(
        ROLLBACK,
        'STATE_DIR="$1"; verify_owned_final_path key-owned "$2" "$3"',
        state,
        hash_record,
        final_path,
    )

    assert completed.returncode == 0, completed.stderr
    assert partial_stage.read_text(encoding="utf-8") == "partial"


def test_apt_calls_use_only_isolated_docker_source_configuration(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log = tmp_path / "apt.log"
    _write_executable(fake_bin / "install", "#!/bin/sh\nexit 0\n")
    _write_executable(
        fake_bin / "apt-get",
        '#!/bin/sh\nprintf "apt-get:%s\\n" "$*" >> "$P014_FAKE_APT_LOG"\nexit 0\n',
    )
    _write_executable(
        fake_bin / "apt-cache",
        "#!/bin/sh\n"
        'printf "apt-cache:%s\\n" "$*" >> "$P014_FAKE_APT_LOG"\n'
        "printf '  Candidate: 1.0\\n'\n"
        "exit 0\n",
    )

    completed = _run_sourced(
        INSTALLER,
        'configure_isolated_apt "$1"; isolated_apt_update; '
        "isolated_apt_policy docker-ce >/dev/null; "
        "isolated_apt_simulate_install docker-ce=1.0 >/dev/null; "
        "isolated_apt_install docker-ce=1.0",
        tmp_path / "state",
        env={
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "P014_FAKE_APT_LOG": str(log),
        },
    )

    assert completed.returncode == 0, completed.stderr
    calls = log.read_text(encoding="utf-8").splitlines()
    assert len(calls) == 4
    for call in calls:
        assert "Dir::Etc::sourcelist=/etc/apt/sources.list.d/docker.sources" in call
        assert "Dir::Etc::sourceparts=-" in call
        assert f"Dir::State::lists={tmp_path}/state/apt-lists" in call
        assert f"Dir::Cache::archives={tmp_path}/state/apt-archives" in call
        assert "APT::Install-Recommends=false" in call
        assert "APT::Install-Suggests=false" in call
    assert "--simulate install -y --no-install-recommends docker-ce=1.0" in calls[2]
    assert "install -y --no-install-recommends docker-ce=1.0" in calls[3]


def test_simulation_rejects_new_dependency_outside_fixed_package_set(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    simulation = tmp_path / "simulation.txt"
    _write_executable(fake_bin / "install", "#!/bin/sh\nexit 0\n")
    _write_executable(
        fake_bin / "apt-get",
        "#!/bin/sh\n"
        "printf 'Inst docker-ce (1.0 Docker:stable [amd64])\\n'\n"
        "printf 'Inst docker-ce-cli (1.0 Docker:stable [amd64])\\n'\n"
        "printf 'Inst containerd.io (1.0 Docker:stable [amd64])\\n'\n"
        "printf 'Inst docker-buildx-plugin (1.0 Docker:stable [amd64])\\n'\n"
        "printf 'Inst docker-compose-plugin (1.0 Docker:stable [amd64])\\n'\n"
        "printf 'Inst unexpected-dependency (1.0 foreign [amd64])\\n'\n"
        "exit 0\n",
    )

    completed = _run_sourced(
        INSTALLER,
        'configure_isolated_apt "$1"; '
        'isolated_apt_simulate_install docker-ce=1.0 > "$2"; '
        'validate_apt_simulation "$2"',
        tmp_path / "state",
        simulation,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert completed.returncode != 0
    assert "P014_DOCKER_INSTALL_SIMULATION_PACKAGE_SET_INVALID" in completed.stderr


def test_downloaded_keyring_rejects_extra_primary_key(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    key = tmp_path / "docker.asc"
    evidence = tmp_path / "key.colons"
    key.touch()
    _write_executable(
        fake_bin / "gpg",
        "#!/bin/sh\n"
        "printf 'pub:::::::::\\n'\n"
        f"printf 'fpr:::::::::{EXPECTED_FINGERPRINT}:\\n'\n"
        "printf 'pub:::::::::\\n'\n"
        "printf 'fpr:::::::::AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA:\\n'\n",
    )

    completed = _run_sourced(
        INSTALLER,
        'validate_downloaded_keyring "$1" "$2"',
        key,
        evidence,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert completed.returncode != 0
    assert "P014_DOCKER_INSTALL_KEY_PRIMARY_SET_INVALID" in completed.stderr


def test_downloaded_keyring_accepts_one_primary_with_subkey(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    key = tmp_path / "docker.asc"
    evidence = tmp_path / "key.colons"
    key.touch()
    _write_executable(
        fake_bin / "gpg",
        "#!/bin/sh\n"
        "printf 'pub:::::::::\\n'\n"
        f"printf 'fpr:::::::::{EXPECTED_FINGERPRINT}:\\n'\n"
        "printf 'sub:::::::::\\n'\n"
        "printf 'fpr:::::::::BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB:\\n'\n",
    )

    completed = _run_sourced(
        INSTALLER,
        'validate_downloaded_keyring "$1" "$2"',
        key,
        evidence,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert completed.returncode == 0, completed.stderr


def test_term_signal_runs_armed_rollback_and_exits_143(tmp_path: Path) -> None:
    fake_rollback = tmp_path / "rollback"
    signal_log = tmp_path / "signal.log"
    state = tmp_path / "state"
    state.mkdir()
    _write_executable(
        fake_rollback,
        '#!/bin/sh\nprintf "called\\n" > "$P014_SIGNAL_LOG"\nexit 0\n',
    )

    completed = _run_sourced(
        INSTALLER,
        'ROLLBACK="$1"; STATE_DIR="$2"; ROLLBACK_OUTPUT="$3"; '
        "TRANSACTION_ACTIVE=1; trap 'handle_install_signal TERM' TERM; kill -TERM $$",
        fake_rollback,
        state,
        tmp_path / "rollback.json",
        env={"P014_SIGNAL_LOG": str(signal_log)},
    )

    assert completed.returncode == 143
    assert signal_log.read_text(encoding="utf-8") == "called\n"
    assert "starting deterministic rollback" in completed.stderr


def test_int_signal_runs_armed_rollback_and_exits_130(tmp_path: Path) -> None:
    fake_rollback = tmp_path / "rollback"
    signal_log = tmp_path / "signal.log"
    state = tmp_path / "state"
    state.mkdir()
    _write_executable(
        fake_rollback,
        '#!/bin/sh\nprintf "called\\n" > "$P014_SIGNAL_LOG"\nexit 0\n',
    )

    completed = _run_sourced(
        INSTALLER,
        'ROLLBACK="$1"; STATE_DIR="$2"; ROLLBACK_OUTPUT="$3"; '
        "TRANSACTION_ACTIVE=1; trap 'handle_install_signal INT' INT; kill -INT $$",
        fake_rollback,
        state,
        tmp_path / "rollback.json",
        env={"P014_SIGNAL_LOG": str(signal_log)},
    )

    assert completed.returncode == 130
    assert signal_log.read_text(encoding="utf-8") == "called\n"
    assert "starting deterministic rollback" in completed.stderr


def test_err_trap_runs_armed_rollback(tmp_path: Path) -> None:
    fake_rollback = tmp_path / "rollback"
    signal_log = tmp_path / "signal.log"
    state = tmp_path / "state"
    state.mkdir()
    _write_executable(
        fake_rollback,
        '#!/bin/sh\nprintf "called\\n" > "$P014_SIGNAL_LOG"\nexit 0\n',
    )

    completed = _run_sourced(
        INSTALLER,
        'ROLLBACK="$1"; STATE_DIR="$2"; ROLLBACK_OUTPUT="$3"; '
        "TRANSACTION_ACTIVE=1; trap 'handle_install_error $?' ERR; false",
        fake_rollback,
        state,
        tmp_path / "rollback.json",
        env={"P014_SIGNAL_LOG": str(signal_log)},
    )

    assert completed.returncode == 1
    assert signal_log.read_text(encoding="utf-8") == "called\n"
    assert "p014-docker-install-failed:ERR" in completed.stderr
