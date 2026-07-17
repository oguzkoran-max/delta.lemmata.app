#!/usr/bin/env python3
"""Fail-closed static validation for the P014 public-alpha deployment package."""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT = ROOT / "deploy" / "public-alpha"
GATEWAY_LOCK = ROOT / "containers" / "gateway-images.lock.json"
RUNBOOK = DEPLOYMENT / "README.md"
IMAGE_VERIFIER = ROOT / "scripts" / "verify_p014_image.py"
SECRET_NAMES = (
    "DELTA_JOB_OWNER_SECRET_HEX",
    "DELTA_PREPARATION_AUTHORITY_SECRET_HEX",
    "DELTA_RECOVERY_RECEIPT_SECRET_HEX",
)
GATEWAY_REFERENCE = (
    "nginxinc/nginx-unprivileged:1.30.3-alpine-slim@"
    "sha256:3b24c4bfb2b9f60359b1475605ca1c8ed6e4963eb8369c6835be4d96bdb3ea81"
)
GATEWAY_TEMP_PATHS = (
    "/tmp/client_temp",
    "/tmp/proxy_temp",
    "/tmp/fastcgi_temp",
    "/tmp/uwsgi_temp",
    "/tmp/scgi_temp",
)


class DeploymentValidationError(RuntimeError):
    """A deterministic deployment-package rejection."""


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys before deployment semantics are inspected."""


def _construct_mapping(
    loader: UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DeploymentValidationError("P014_DUPLICATE_YAML_KEY")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise DeploymentValidationError(code)


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), code)
    return value


def _require_ordered(text: str, tokens: Sequence[str], code: str) -> None:
    cursor = -1
    for token in tokens:
        position = text.find(token, cursor + 1)
        _require(position >= 0, code)
        cursor = position


def _slice_between(text: str, start: str, end: str, code: str) -> str:
    start_index = text.find(start)
    _require(start_index >= 0, code)
    end_index = text.find(end, start_index + len(start))
    _require(end_index >= 0, code)
    return text[start_index:end_index]


def _first_bash_block_after(text: str, heading: str, code: str) -> str:
    heading_index = text.find(heading)
    _require(heading_index >= 0, code)
    block_start = text.find("```bash\n", heading_index)
    _require(block_start >= 0, code)
    content_start = block_start + len("```bash\n")
    block_end = text.find("\n```", content_start)
    _require(block_end >= 0, code)
    return text[content_start:block_end]


def _validate_runbook_contracts(runbook: str) -> None:
    required = (
        "p014-host-gate/1.3.0",
        "--preflight /root/p014-host-evidence/pre-docker.json",
        "P014_POST_DOCKER_EXTERNAL_8502_REACHABLE",
        "cleanup_registry_auth()",
        "trap cleanup_registry_auth EXIT",
        'python3 "$RELEASE_ROOT/scripts/verify_p014_image.py"',
        '--image-reference "$DELTA_IMAGE"',
        '--source-sha "$SOURCE_SHA"',
        "cleanup_failed_first_release()",
        "trap cleanup_failed_first_release EXIT",
        "PRE_CADDY_GATES_COMPLETE=1",
        "### Pre-Caddy rollback",
        "### Post-Caddy rollback",
        "bounded, isolated synthetic stylo handoff",
        "python3 scripts/p014_load_gate.py",
    )
    _require(all(token in runbook for token in required), "P014_RUNBOOK_CONTRACT_INCOMPLETE")
    _require(
        "trap cleanup_registry_auth EXIT INT TERM" not in runbook,
        "P014_REGISTRY_TRAP_NOT_EXIT_ONLY",
    )

    phase_3 = _slice_between(
        runbook,
        "## Phase 3: Install and Compare the Container Runtime",
        "## Phase 4: Install an Immutable Release",
        "P014_RUNBOOK_PHASE_3_INVALID",
    )
    _require(
        "--preflight /root/p014-host-evidence/pre-docker.json" in phase_3
        and "python3 scripts/p014_host_gate.py pre-mutation" not in phase_3
        and "--preflight /root/p014-host-evidence/pre-mutation.json" not in phase_3,
        "P014_RUNBOOK_PREFLIGHT_CONTRACT_INVALID",
    )

    _require_ordered(
        runbook,
        (
            "scripts/p014_install_docker_ubuntu.sh",
            "P014_POST_DOCKER_EXTERNAL_8502_REACHABLE",
            'docker pull "$DELTA_IMAGE"',
            'python3 "$RELEASE_ROOT/scripts/verify_p014_image.py"',
            "systemctl enable --now delta-public-alpha.service",
            "scripts/smoke_p014_stack.sh",
            "python3 scripts/inspect_p014_runtime.py",
            "python3 scripts/p014_host_gate.py delta-idle",
            "PRE_CADDY_GATES_COMPLETE=1",
            "## Phase 5: Obtain Separate Pre-Caddy Owner Authorization",
        ),
        "P014_RUNBOOK_PHASE_ORDER_INVALID",
    )
    _require_ordered(
        runbook,
        (
            "trap cleanup_failed_first_release EXIT",
            'sed "s|^$TEMPLATE_WORKDIR$|$RELEASE_WORKDIR|"',
            'mv -f "$UNIT_STAGE" "$UNIT_PATH"',
            "systemctl enable --now delta-public-alpha.service",
        ),
        "P014_STARTUP_CLEANUP_ARMED_TOO_LATE",
    )

    startup = _slice_between(
        runbook,
        "cleanup_failed_first_release() {",
        "trap cleanup_failed_first_release EXIT",
        "P014_STARTUP_CLEANUP_BLOCK_INVALID",
    )
    startup_required = (
        "systemctl stop delta-public-alpha.service",
        "systemctl disable delta-public-alpha.service",
        '"${COMPOSE[@]}" down --remove-orphans --timeout 75',
        'remaining_containers=$("${COMPOSE[@]}" ps --quiet)',
        "remaining_listeners=$(ss -H -ltn 'sport = :8502')",
        'rm -f -- "$UNIT_STAGE" "$UNIT_PATH"',
        "systemctl daemon-reload",
        "P014_PRE_CADDY_CLEANUP_INCOMPLETE",
    )
    _require(
        all(token in startup for token in startup_required),
        "P014_STARTUP_CLEANUP_BLOCK_INVALID",
    )
    _require(
        "|| true" not in startup and "2>/dev/null" not in startup,
        "P014_CRITICAL_CLEANUP_FAILURE_SUPPRESSED",
    )

    registry = _slice_between(
        runbook,
        "cleanup_registry_auth() {",
        "trap cleanup_registry_auth EXIT",
        "P014_REGISTRY_CLEANUP_BLOCK_INVALID",
    )
    _require(
        "trap - EXIT" in registry
        and 'rm -rf -- "$DOCKER_CONFIG"' in registry
        and "P014_REGISTRY_AUTH_CLEANUP_FAILED" in registry,
        "P014_REGISTRY_CLEANUP_BLOCK_INVALID",
    )

    unit_required = (
        'RELEASE_ROOT="/opt/delta-public-alpha/releases/$SOURCE_SHA"',
        'RELEASE_WORKDIR="WorkingDirectory=$RELEASE_ROOT/deploy/public-alpha"',
        "! grep -Fq '/opt/delta-public-alpha/current' \"$UNIT_STAGE\"",
        'mv -f "$UNIT_STAGE" "$UNIT_PATH"',
    )
    _require(all(token in runbook for token in unit_required), "P014_UNIT_RELEASE_NOT_IMMUTABLE")

    pre_caddy = _first_bash_block_after(
        runbook,
        "### Pre-Caddy rollback",
        "P014_PRE_CADDY_ROLLBACK_INVALID",
    )
    _require(
        "/etc/caddy/" not in pre_caddy
        and "systemctl stop delta-public-alpha.service" in pre_caddy
        and '"${COMPOSE[@]}" down --remove-orphans --timeout 75' in pre_caddy
        and 'REMAINING_CONTAINERS=$("${COMPOSE[@]}" ps --quiet)' in pre_caddy
        and "REMAINING_LISTENERS=$(ss -H -ltn 'sport = :8502')" in pre_caddy,
        "P014_PRE_CADDY_ROLLBACK_INVALID",
    )


def _validate_image_verifier_contract() -> None:
    source = IMAGE_VERIFIER.read_text(encoding="utf-8")
    required = (
        'docker_binary, "image", "inspect", image_reference',
        'REVISION_LABEL = "org.opencontainers.image.revision"',
        "P014_IMAGE_REFERENCE_NOT_IMMUTABLE",
        "P014_IMAGE_DIGEST_MISMATCH",
        "P014_IMAGE_REVISION_MISMATCH",
    )
    _require(all(token in source for token in required), "P014_IMAGE_VERIFIER_INCOMPLETE")


def _load_compose(path: Path) -> Mapping[str, Any]:
    try:
        loaded = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise DeploymentValidationError("P014_COMPOSE_PARSE_FAILED") from error
    return _mapping(loaded, "P014_COMPOSE_NOT_MAPPING")


def _has_hardening(service: Mapping[str, Any], *, pids: int, cpus: str, memory: str) -> bool:
    return (
        service.get("read_only") is True
        and service.get("cap_drop") == ["ALL"]
        and "no-new-privileges:true" in service.get("security_opt", [])
        and service.get("pids_limit") == pids
        and str(service.get("cpus")) == cpus
        and str(service.get("mem_limit")) == memory
        and str(service.get("memswap_limit")) == memory
        and service.get("restart") == "on-failure:3"
    )


def _validate_compose(compose: Mapping[str, Any]) -> None:
    _require(compose.get("name") == "delta-public-alpha", "P014_PROJECT_NAME_INVALID")
    services = _mapping(compose.get("services"), "P014_SERVICES_INVALID")
    _require(set(services) == {"app", "gateway"}, "P014_SERVICE_SET_INVALID")
    app = _mapping(services["app"], "P014_APP_INVALID")
    gateway = _mapping(services["gateway"], "P014_GATEWAY_INVALID")

    _require(
        app.get("image") == "${DELTA_IMAGE:?Set DELTA_IMAGE to an immutable Delta image reference}",
        "P014_APP_IMAGE_NOT_REQUIRED",
    )
    _require(app.get("platform") == "linux/amd64", "P014_APP_PLATFORM_INVALID")
    _require(app.get("user") == "10001:10001", "P014_APP_USER_INVALID")
    _require(app.get("ports") is None, "P014_APP_MUST_NOT_PUBLISH_PORT")
    _require(app.get("expose") == ["8501"], "P014_APP_EXPOSE_INVALID")
    _require(app.get("networks") == ["delta_internal"], "P014_APP_NETWORK_INVALID")
    _require(
        _has_hardening(app, pids=128, cpus="1.50", memory="1536m"),
        "P014_APP_HARDENING_INVALID",
    )
    app_environment = _mapping(app.get("environment"), "P014_APP_ENVIRONMENT_INVALID")
    _require(app_environment.get("DELTA_ENV") == "production", "P014_PROFILE_INVALID")
    _require(
        app_environment.get("DELTA_EXTERNAL_NETWORK") == "disabled",
        "P014_EGRESS_POLICY_INVALID",
    )
    _require(
        app_environment.get("DELTA_RUNTIME_ROOT") == "/var/lib/delta/runtime",
        "P014_RUNTIME_ROOT_INVALID",
    )
    _require(len(app.get("env_file", [])) == 1, "P014_SECRET_FILE_INVALID")
    app_tmpfs = app.get("tmpfs", [])
    _require(
        any(str(item).startswith("/var/lib/delta/runtime:") for item in app_tmpfs),
        "P014_RUNTIME_TMPFS_MISSING",
    )
    _require(
        any("size=512m" in str(item) and "mode=0700" in str(item) for item in app_tmpfs),
        "P014_RUNTIME_TMPFS_LIMIT_INVALID",
    )
    _require("healthcheck" in app, "P014_APP_HEALTHCHECK_MISSING")
    _require(app.get("stop_grace_period") == "75s", "P014_APP_STOP_GRACE_INVALID")

    _require(gateway.get("image") == GATEWAY_REFERENCE, "P014_GATEWAY_IMAGE_INVALID")
    _require(gateway.get("platform") == "linux/amd64", "P014_GATEWAY_PLATFORM_INVALID")
    _require(gateway.get("user") == "101:101", "P014_GATEWAY_USER_INVALID")
    _require(
        gateway.get("ports") == ["127.0.0.1:8502:8080"],
        "P014_GATEWAY_BIND_INVALID",
    )
    _require(
        gateway.get("networks") == ["delta_internal", "delta_edge"],
        "P014_GATEWAY_NETWORK_INVALID",
    )
    _require(
        _has_hardening(gateway, pids=64, cpus="0.25", memory="128m"),
        "P014_GATEWAY_HARDENING_INVALID",
    )
    gateway_volumes = gateway.get("volumes", [])
    _require(
        all("/var/cache/nginx" not in str(mount) for mount in gateway_volumes),
        "P014_GATEWAY_CACHE_MOUNT_FORBIDDEN",
    )
    _require(
        gateway_volumes == ["./nginx.conf:/etc/nginx/nginx.conf:ro"],
        "P014_GATEWAY_MOUNT_INVALID",
    )
    _require(
        gateway.get("tmpfs") == ["/tmp:rw,nosuid,nodev,noexec,size=32m,mode=0700,uid=101,gid=101"],
        "P014_GATEWAY_TMPFS_INVALID",
    )
    gateway_entrypoint = gateway.get("entrypoint", [])
    _require(
        isinstance(gateway_entrypoint, list)
        and len(gateway_entrypoint) == 3
        and all(path in str(gateway_entrypoint[2]) for path in GATEWAY_TEMP_PATHS),
        "P014_GATEWAY_TEMP_SETUP_INCOMPLETE",
    )
    _require("healthcheck" in gateway, "P014_GATEWAY_HEALTHCHECK_MISSING")

    networks = _mapping(compose.get("networks"), "P014_NETWORKS_INVALID")
    _require(set(networks) == {"delta_internal", "delta_edge"}, "P014_NETWORK_SET_INVALID")
    internal = _mapping(networks["delta_internal"], "P014_INTERNAL_NETWORK_INVALID")
    _require(internal.get("internal") is True, "P014_INTERNAL_NETWORK_NOT_ISOLATED")
    _require(internal.get("attachable") is False, "P014_INTERNAL_NETWORK_ATTACHABLE")
    edge = _mapping(networks["delta_edge"], "P014_EDGE_NETWORK_INVALID")
    _require(edge.get("internal") is False, "P014_EDGE_NETWORK_INTERNAL")
    _require(edge.get("attachable") is False, "P014_EDGE_NETWORK_ATTACHABLE")


def _validate_gateway_lock() -> None:
    lock = json.loads(GATEWAY_LOCK.read_text(encoding="utf-8"))
    _require(lock["repository"] == "nginxinc/nginx-unprivileged", "P014_LOCK_REPOSITORY")
    _require(lock["tag"] == "1.30.3-alpine-slim", "P014_LOCK_TAG")
    _require(
        lock["manifest_list_digest"]
        == "sha256:3b24c4bfb2b9f60359b1475605ca1c8ed6e4963eb8369c6835be4d96bdb3ea81",
        "P014_LOCK_MANIFEST_DIGEST",
    )
    _require(
        lock["linux_amd64_digest"]
        == "sha256:679095599879759174acfd716da4ca06a4b14dcbf5adb1c2ec60c64182668c90",
        "P014_LOCK_AMD64_DIGEST",
    )
    _require(lock["source"] == "Docker Registry HTTP API V2", "P014_LOCK_SOURCE")


def _validate_text_contracts() -> None:
    dockerfile = (ROOT / "containers" / "Dockerfile").read_text(encoding="utf-8")
    _require("groupadd --gid 10001 delta" in dockerfile, "P014_DOCKER_GID_MISSING")
    _require("useradd --uid 10001 --gid 10001" in dockerfile, "P014_DOCKER_UID_MISSING")
    _require(
        dockerfile.index("useradd --uid 10001 --gid 10001")
        < dockerfile.index("ENV HOME=/home/delta")
        < dockerfile.index("USER delta"),
        "P014_RUNTIME_HOME_ORDER_INVALID",
    )
    _require("COPY .streamlit ./.streamlit" in dockerfile, "P014_STREAMLIT_CONFIG_NOT_COPIED")
    _require("HEALTHCHECK" in dockerfile, "P014_IMAGE_HEALTHCHECK_MISSING")
    _require("ARG DELTA_BUILD_ID=development" in dockerfile, "P014_IMAGE_BUILD_ID_MISSING")
    _require(
        'org.opencontainers.image.revision="${DELTA_BUILD_ID}"' in dockerfile,
        "P014_IMAGE_REVISION_LABEL_MISSING",
    )
    _require(
        'org.opencontainers.image.source="https://github.com/oguzkoran-max/delta.lemmata.app"'
        in dockerfile,
        "P014_IMAGE_SOURCE_LABEL_MISSING",
    )
    _require(
        'CMD ["/opt/delta/.venv/bin/streamlit", "run", "app.py"' in dockerfile,
        "P014_RUNTIME_COMMAND_INVALID",
    )

    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    _require(
        '--build-arg DELTA_BUILD_ID="$GITHUB_SHA"' in ci,
        "P014_CI_BUILD_ID_NOT_BOUND",
    )

    publisher = (ROOT / ".github" / "workflows" / "p014-publish-image.yml").read_text(
        encoding="utf-8"
    )
    required_publisher = (
        "workflow_dispatch:",
        "actions: read",
        "contents: read",
        "packages: write",
        "persist-credentials: false",
        "ref: ${{ inputs.source_sha }}",
        "head_sha=$REQUESTED_SHA&status=success",
        '--build-arg DELTA_BUILD_ID="$SOURCE_SHA"',
        "./scripts/run_p014_runtime_gate.sh",
        'IMAGE_TAG="$IMAGE_REPOSITORY:sha-$SOURCE_SHA"',
        "IMAGE_DIGEST_REFERENCE",
        "Mutable `latest` tag: not published",
    )
    _require(
        all(item in publisher for item in required_publisher),
        "P014_PUBLISH_WORKFLOW_INCOMPLETE",
    )
    _require("pull_request:" not in publisher, "P014_PUBLISH_TRIGGER_TOO_BROAD")
    _require("\n  push:" not in publisher, "P014_PUBLISH_TRIGGER_TOO_BROAD")
    _require("actions/upload-artifact" not in publisher, "P014_PUBLISH_ARTIFACT_FORBIDDEN")

    nginx = (DEPLOYMENT / "nginx.conf").read_text(encoding="utf-8")
    required_nginx = (
        "server_name delta.lemmata.app;",
        "return 421;",
        "client_max_body_size 26m;",
        "map $uri $delta_dynamic_rate_key",
        "map $uri $delta_static_rate_key",
        "limit_req_zone $delta_dynamic_rate_key zone=delta_dynamic_requests:1m rate=120r/m;",
        "limit_req_zone $delta_static_rate_key zone=delta_static_requests:1m rate=600r/m;",
        "limit_req zone=delta_dynamic_requests burst=60 nodelay;",
        "limit_req zone=delta_static_requests burst=120 nodelay;",
        "limit_conn_zone $binary_remote_addr",
        "proxy_connect_timeout 5s;",
        "proxy_read_timeout 75s;",
        "proxy_set_header Host $http_host;",
        "proxy_set_header X-Forwarded-Host $http_host;",
        "proxy_set_header X-Forwarded-Proto https;",
        "proxy_set_header Upgrade $http_upgrade;",
        "proxy_set_header Connection $connection_upgrade;",
        'add_header X-Frame-Options "DENY" always;',
        "access_log off;",
        "client_body_temp_path /tmp/client_temp 1 2;",
        "proxy_temp_path /tmp/proxy_temp 1 2;",
        "fastcgi_temp_path /tmp/fastcgi_temp 1 2;",
        "uwsgi_temp_path /tmp/uwsgi_temp 1 2;",
        "scgi_temp_path /tmp/scgi_temp 1 2;",
    )
    _require(all(item in nginx for item in required_nginx), "P014_GATEWAY_POLICY_INCOMPLETE")
    _require(
        '~^/static/ "";' in nginx and "~^/static/ $binary_remote_addr;" in nginx,
        "P014_GATEWAY_RATE_CLASSIFICATION_INCOMPLETE",
    )
    _require("$delta_forwarded_proto" not in nginx, "P014_GATEWAY_SCHEME_NOT_PINNED")
    _require("/var/cache/nginx" not in nginx, "P014_GATEWAY_CACHE_PATH_FORBIDDEN")

    caddy = (DEPLOYMENT / "Caddyfile.delta.example").read_text(encoding="utf-8")
    _require(caddy.count("delta.lemmata.app {") == 1, "P014_CADDY_HOST_INVALID")
    _require("reverse_proxy 127.0.0.1:8502" in caddy, "P014_CADDY_UPSTREAM_INVALID")
    _require("Strict-Transport-Security" in caddy, "P014_CADDY_TLS_HEADER_MISSING")

    service = (DEPLOYMENT / "delta-public-alpha.service").read_text(encoding="utf-8")
    _require("WorkingDirectory=/opt/delta-public-alpha/current" in service, "P014_UNIT_ROOT")
    _require("--project-name delta-public-alpha" in service, "P014_UNIT_PROJECT")
    _require("EnvironmentFile=/etc/delta-public-alpha/deployment.env" in service, "P014_UNIT_ENV")

    streamlit = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    _require(streamlit["server"]["enableCORS"] is True, "P014_CORS_DISABLED")
    _require(streamlit["server"]["enableXsrfProtection"] is True, "P014_XSRF_DISABLED")

    runtime_example = (DEPLOYMENT / "runtime.env.example").read_text(encoding="utf-8")
    root_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    _require(
        all(runtime_example.count(name) == 1 for name in SECRET_NAMES),
        "P014_RUNTIME_SECRET_TEMPLATE_INVALID",
    )
    _require(
        all(name in root_example for name in SECRET_NAMES), "P014_ROOT_SECRET_TEMPLATE_INVALID"
    )
    _require(
        re.search(r"(?:SECRET_HEX)=([0-9a-f]{64})(?:\n|$)", runtime_example) is None,
        "P014_REAL_SECRET_IN_TEMPLATE",
    )

    operational = "\n".join(
        (DEPLOYMENT / name).read_text(encoding="utf-8")
        for name in (
            "compose.yml",
            "nginx.conf",
            "Caddyfile.delta.example",
            "delta-public-alpha.service",
        )
    ).casefold()
    forbidden = ("/opt/lemmata", "lemmata.service", "127.0.0.1:8501:8501")
    _require(all(item not in operational for item in forbidden), "P014_LEMMATA_BOUNDARY_VIOLATION")

    host_gate = (ROOT / "scripts" / "p014_host_gate.py").read_text(encoding="utf-8")
    installer = (ROOT / "scripts" / "p014_install_docker_ubuntu.sh").read_text(encoding="utf-8")
    rollback = (ROOT / "scripts" / "p014_rollback_docker_ubuntu.sh").read_text(encoding="utf-8")
    load_gate = (ROOT / "scripts" / "p014_load_gate.py").read_text(encoding="utf-8")
    _require(
        all(
            token in host_gate
            for token in (
                'SCHEMA_VERSION = "1.3.0"',
                '"pre-docker"',
                '"pre-mutation"',
                '"post-docker"',
                '"delta-idle"',
                '"post-rollback"',
                "P014_LEMMATA_P95_BUDGET_EXCEEDED",
                "P014_DELTA_LISTENER_SET_INVALID",
                "P014_CADDYFILE_CHANGED",
                "P014_BASELINE_HOST_OR_BOOT_CHANGED",
                "P014_DOCKER_PACKAGE_SET_INVALID",
                "P014_DOCKER_CANDIDATE_VERSION_MISMATCH",
                "P014_DOCKER_PACKAGE_ORIGIN_INVALID",
                "9DC858229FC7DD38854AE2D88D81803C0EBFCD88",
            )
        ),
        "P014_HOST_GATE_INCOMPLETE",
    )
    _require(
        all(
            token in load_gate
            for token in (
                'SCHEMA_VERSION = "1.2.0"',
                'REQUIRED_HOST_GATE_SCHEMA_VERSION = "1.3.0"',
                "bounded-synthetic-stylo-coexistence-v3",
                "isolated-p006-scientific-handoff-loop-v1",
                "P014_LOAD_BOUNDED_ANALYSIS_FAILED",
                "P014_LOAD_LEMMATA_P95_BUDGET_EXCEEDED",
                "P014_LOAD_HOST_CAPACITY_FAILED",
                "P014_LOAD_LISTENER_SET_INVALID",
                'failures.append(f"P014_LOAD_{role.upper()}_STATE_FAILED")',
                'failures.append(f"P014_LOAD_{role.upper()}_LIMIT_FAILED")',
            )
        ),
        "P014_LOAD_GATE_INCOMPLETE",
    )
    _require(
        all(
            token in installer
            for token in (
                "https://download.docker.com/linux/ubuntu/gpg",
                "9DC858229FC7DD38854AE2D88D81803C0EBFCD88",
                "--no-install-recommends",
                'SPECS+=("$package=$candidate")',
                "p014_rollback_docker_ubuntu.sh",
                "rollback-armed",
                "rollback-disarmed",
            )
        ),
        "P014_DOCKER_INSTALLER_INCOMPLETE",
    )
    _require(
        all(
            token in rollback
            for token in (
                "PACKAGE_ALLOWLIST",
                "post-rollback",
                "P014_DOCKER_ROLLBACK_NOT_ARMED",
                "iptables-restore",
                "ip6tables-restore",
            )
        ),
        "P014_DOCKER_ROLLBACK_INCOMPLETE",
    )
    _require(
        all(
            forbidden_action not in installer + rollback
            for forbidden_action in ("systemctl restart lemmata", "systemctl stop lemmata")
        ),
        "P014_HOST_SCRIPT_TOUCHES_LEMMATA",
    )


def validate(root: Path = ROOT) -> None:
    _require(root.resolve() == ROOT.resolve(), "P014_UNSUPPORTED_ROOT")
    compose = _load_compose(DEPLOYMENT / "compose.yml")
    _validate_compose(compose)
    _validate_gateway_lock()
    _validate_text_contracts()
    _validate_runbook_contracts(RUNBOOK.read_text(encoding="utf-8"))
    _validate_image_verifier_contract()


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    validate()
    print("p014-deployment-package-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
