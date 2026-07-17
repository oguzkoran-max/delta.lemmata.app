#!/usr/bin/env bash
set -Eeuo pipefail

umask 077
export DEBIAN_FRONTEND=noninteractive
export LC_ALL=C
unset APT_CONFIG

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
HOST_GATE="$SCRIPT_DIR/p014_host_gate.py"
KEYRING_DIR=/etc/apt/keyrings
DOCKER_KEY=$KEYRING_DIR/docker.asc
DOCKER_KEY_STAGE=$KEYRING_DIR/.docker.asc.p014
DOCKER_SOURCE=/etc/apt/sources.list.d/docker.sources
DOCKER_SOURCE_STAGE=/etc/apt/sources.list.d/.docker.sources.p014
PACKAGE_NAMES=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
PACKAGE_ALLOWLIST='^(docker-ce|docker-ce-cli|containerd.io|docker-buildx-plugin|docker-compose-plugin)(:amd64)?$'
RUNTIME_UNITS=(docker.socket docker.service containerd.service)
STATE_DIR=
OUTPUT=
APPLY=0

usage() {
  echo "usage: $0 --state-dir PATH --output PATH --apply" >&2
  exit 2
}

fail() {
  echo "$1" >&2
  return 1
}

validate_rollback_preflight() {
  local path=$1
  python3 - "$path" <<'PY'
import json
import os
import stat
import sys


def reject_constant(item):
    raise ValueError(f"invalid JSON constant: {item}")


def fail(code):
    print(code, file=sys.stderr)
    raise SystemExit(1)


path = sys.argv[1]
try:
    info = os.stat(path)
    with open(path, encoding="utf-8") as handle:
        value = json.load(handle, parse_constant=reject_constant)
except (OSError, TypeError, ValueError, json.JSONDecodeError):
    fail("P014_DOCKER_ROLLBACK_PREFLIGHT_INVALID")

if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
    fail("P014_DOCKER_ROLLBACK_PREFLIGHT_PERMISSIONS_INVALID")
if not isinstance(value, dict) or value.get("schema_version") != "1.3.0":
    fail("P014_DOCKER_ROLLBACK_PREFLIGHT_SCHEMA_INVALID")
if value.get("capture_mode") != "live" or value.get("phase") != "pre-docker":
    fail("P014_DOCKER_ROLLBACK_PREFLIGHT_PHASE_INVALID")
if value.get("gate") != {"passed": True, "failures": []}:
    fail("P014_DOCKER_ROLLBACK_PREFLIGHT_NOT_ACCEPTED")
try:
    forwarding = value["host"]["forwarding"]
    ipv4 = forwarding["ipv4"]
    ipv6 = forwarding["ipv6"]
except (KeyError, TypeError):
    fail("P014_DOCKER_ROLLBACK_FORWARDING_INVALID")
if type(ipv4) is not int or type(ipv6) is not int or ipv4 not in (0, 1) or ipv6 not in (0, 1):
    fail("P014_DOCKER_ROLLBACK_FORWARDING_INVALID")
print(ipv4, ipv6)
PY
}

validate_firewall_evidence() {
  local baseline_path=$1
  local evidence_root=$2
  python3 - "$baseline_path" "$evidence_root" <<'PY'
import hashlib
import json
import pathlib
import sys


def fail(code):
    print(code, file=sys.stderr)
    raise SystemExit(1)


try:
    baseline = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = pathlib.Path(sys.argv[2])
    names = {
        "nftables": root / "firewall-nftables.before",
        "iptables": root / "firewall-iptables.before",
        "ip6tables": root / "firewall-ip6tables.before",
    }
    expected = baseline["host"]["firewall"]
except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
    fail("P014_DOCKER_ROLLBACK_FIREWALL_EVIDENCE_INVALID")

for name, path in names.items():
    if not path.is_file():
        fail(f"P014_DOCKER_ROLLBACK_FIREWALL_CAPTURE_MISSING:{name}")
    try:
        payload = path.read_bytes()
        text = payload.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        fail(f"P014_DOCKER_ROLLBACK_FIREWALL_CAPTURE_INVALID:{name}")
    observed = {
        "line_count": sum(bool(line.strip()) for line in text.splitlines()),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    if observed != expected.get(name):
        fail(f"P014_DOCKER_ROLLBACK_FIREWALL_CAPTURE_MISMATCH:{name}")
PY
}

query_package_status() {
  local package=$1
  local status
  local return_code
  if status=$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null); then
    printf '%s\n' "$status"
    return 0
  else
    return_code=$?
  fi
  if [[ $return_code -eq 1 ]]; then
    printf '%s\n' not-installed
    return 0
  fi
  fail "P014_DOCKER_ROLLBACK_PACKAGE_QUERY_FAILED:$package"
}

expected_hash() {
  local hash_file=$1
  local expected
  expected=$(awk 'NR == 1 {print $1}' "$hash_file")
  if [[ ! $expected =~ ^[0-9a-f]{64}$ ]]; then
    fail "P014_DOCKER_ROLLBACK_HASH_RECORD_INVALID"
    return 1
  fi
  printf '%s\n' "$expected"
}

verify_owned_final_path() {
  local marker=$1
  local hash_file=$2
  local final_path=$3
  [[ -f $STATE_DIR/$marker ]] || return 0
  if [[ ! -f $hash_file ]]; then
    fail "P014_DOCKER_ROLLBACK_HASH_RECORD_MISSING:$marker"
    return 1
  fi
  local expected
  if ! expected=$(expected_hash "$hash_file"); then
    return 1
  fi
  [[ -e $final_path ]] || return 0
  if [[ ! -f $final_path || -L $final_path ]]; then
    fail "P014_DOCKER_ROLLBACK_OWNED_PATH_TYPE_INVALID:$final_path"
    return 1
  fi
  local actual
  actual=$(sha256sum "$final_path" | awk '{print $1}')
  if [[ $actual != "$expected" ]]; then
    fail "P014_DOCKER_ROLLBACK_OWNED_PATH_CHANGED:$final_path"
    return 1
  fi
}

inspect_docker_empty() {
  local evidence_root=$1
  local image_ids
  local container_ids
  if ! image_ids=$(docker image ls --all --quiet 2> "$evidence_root/docker-image-inspection.err"); then
    fail "P014_DOCKER_ROLLBACK_IMAGE_INSPECTION_FAILED"
    return 1
  fi
  if [[ -n ${image_ids//[[:space:]]/} ]]; then
    fail "P014_DOCKER_ROLLBACK_IMAGE_PRESENT"
    return 1
  fi
  if ! container_ids=$(
    docker container ls --all --quiet 2> "$evidence_root/docker-container-inspection.err"
  ); then
    fail "P014_DOCKER_ROLLBACK_CONTAINER_INSPECTION_FAILED"
    return 1
  fi
  if [[ -n ${container_ids//[[:space:]]/} ]]; then
    fail "P014_DOCKER_ROLLBACK_CONTAINER_PRESENT"
    return 1
  fi
  printf '%s\n' empty > "$evidence_root/docker-runtime-inspection.txt"
}

inspect_owned_runtime_before_cleanup() {
  local evidence_root=$1
  local load_state
  local active_state
  if ! command -v docker >/dev/null; then
    printf '%s\n' partial-install-docker-cli-absent \
      > "$evidence_root/docker-runtime-inspection.txt"
    return 0
  fi
  if ! load_state=$(unit_load_state docker.service); then
    return 1
  fi
  if [[ $load_state == not-found ]]; then
    printf '%s\n' partial-install-docker-service-absent \
      > "$evidence_root/docker-runtime-inspection.txt"
    return 0
  fi
  if ! active_state=$(systemctl show --property=ActiveState --value docker.service); then
    fail "P014_DOCKER_ROLLBACK_UNIT_ACTIVE_QUERY_FAILED:docker.service"
    return 1
  fi
  case "$active_state" in
    active) inspect_docker_empty "$evidence_root" ;;
    inactive|failed)
      printf 'partial-install-docker-service-%s\n' "$active_state" \
        > "$evidence_root/docker-runtime-inspection.txt"
      ;;
    *)
      fail "P014_DOCKER_ROLLBACK_UNIT_STATE_UNSAFE:docker.service:$active_state"
      return 1
      ;;
  esac
}

unit_load_state() {
  local unit=$1
  local state
  if ! state=$(systemctl show --property=LoadState --value "$unit"); then
    fail "P014_DOCKER_ROLLBACK_UNIT_LOAD_QUERY_FAILED:$unit"
    return 1
  fi
  if [[ -z $state ]]; then
    fail "P014_DOCKER_ROLLBACK_UNIT_LOAD_STATE_INVALID:$unit"
    return 1
  fi
  printf '%s\n' "$state"
}

runtime_units_presence() {
  local unit
  local state
  local present=0
  for unit in "${RUNTIME_UNITS[@]}"; do
    if ! state=$(unit_load_state "$unit"); then
      return 1
    fi
    if [[ $state != not-found ]]; then
      present=1
    fi
  done
  printf '%s\n' "$present"
}

stop_runtime_units() {
  local unit
  local load_state
  local active_state
  local enabled_state=
  local enabled_return=0
  for unit in "${RUNTIME_UNITS[@]}"; do
    if ! load_state=$(unit_load_state "$unit"); then
      return 1
    fi
    [[ $load_state == not-found ]] && continue
    if ! systemctl stop "$unit"; then
      fail "P014_DOCKER_ROLLBACK_UNIT_STOP_FAILED:$unit"
      return 1
    fi
    if ! active_state=$(systemctl show --property=ActiveState --value "$unit"); then
      fail "P014_DOCKER_ROLLBACK_UNIT_ACTIVE_QUERY_FAILED:$unit"
      return 1
    fi
    case "$active_state" in
      inactive|failed) ;;
      *)
        fail "P014_DOCKER_ROLLBACK_UNIT_STILL_ACTIVE:$unit:$active_state"
        return 1
        ;;
    esac

    if enabled_state=$(systemctl is-enabled "$unit" 2>/dev/null); then
      enabled_return=0
    else
      enabled_return=$?
    fi
    case "$enabled_state" in
      enabled|enabled-runtime|linked|linked-runtime|alias)
        if ! systemctl disable "$unit"; then
          fail "P014_DOCKER_ROLLBACK_UNIT_DISABLE_FAILED:$unit"
          return 1
        fi
        ;;
      disabled|static|indirect|generated|transient|masked|not-found)
        ;;
      *)
        fail "P014_DOCKER_ROLLBACK_UNIT_ENABLE_QUERY_FAILED:$unit:$enabled_return"
        return 1
        ;;
    esac
  done
}

prove_runtime_stopped() {
  local unit
  local load_state
  local active_state
  local process_name
  local process_return
  for unit in "${RUNTIME_UNITS[@]}"; do
    if ! load_state=$(unit_load_state "$unit"); then
      return 1
    fi
    [[ $load_state == not-found ]] && continue
    if ! active_state=$(systemctl show --property=ActiveState --value "$unit"); then
      fail "P014_DOCKER_ROLLBACK_UNIT_ACTIVE_QUERY_FAILED:$unit"
      return 1
    fi
    case "$active_state" in
      inactive|failed) ;;
      *)
        fail "P014_DOCKER_ROLLBACK_UNIT_STILL_ACTIVE:$unit:$active_state"
        return 1
        ;;
    esac
  done
  for process_name in dockerd containerd; do
    if pgrep -x "$process_name" >/dev/null; then
      fail "P014_DOCKER_ROLLBACK_PROCESS_STILL_RUNNING:$process_name"
      return 1
    else
      process_return=$?
    fi
    if [[ $process_return -ne 1 ]]; then
      fail "P014_DOCKER_ROLLBACK_PROCESS_QUERY_FAILED:$process_name:$process_return"
      return 1
    fi
  done
}

capture_firewall_residual_file() {
  local name=$1
  shift
  local final_path
  local stage_path
  final_path="$STATE_DIR/firewall-$name.rollback-residual"
  [[ ! -e $final_path ]] || return 0
  stage_path="$STATE_DIR/.firewall-$name.rollback-residual"
  [[ ! -e $stage_path ]] || fail "P014_DOCKER_ROLLBACK_FIREWALL_RESIDUAL_STAGE_EXISTS:$name"
  "$@" > "$stage_path"
  mv "$stage_path" "$final_path"
}

capture_firewall_residual() {
  capture_firewall_residual_file nftables nft list ruleset
  capture_firewall_residual_file iptables iptables-save
  capture_firewall_residual_file ip6tables ip6tables-save
}

restore_firewall_snapshot() {
  capture_firewall_residual
  if [[ ! -s $STATE_DIR/firewall-nftables.before ]] &&
    [[ ! -s $STATE_DIR/firewall-iptables.before ]] &&
    [[ ! -s $STATE_DIR/firewall-ip6tables.before ]]; then
    nft flush ruleset
    touch "$STATE_DIR/firewall-empty-baseline-restored"
    return 0
  fi
  iptables-restore < "$STATE_DIR/firewall-iptables.before"
  ip6tables-restore < "$STATE_DIR/firewall-ip6tables.before"
}

main() {
  while (($#)); do
    case "$1" in
      --state-dir) STATE_DIR=${2:-}; shift 2 ;;
      --output) OUTPUT=${2:-}; shift 2 ;;
      --apply) APPLY=1; shift ;;
      *) usage ;;
    esac
  done

  [[ $APPLY -eq 1 ]] || usage
  [[ $EUID -eq 0 ]] || fail "P014_DOCKER_ROLLBACK_REQUIRES_ROOT"
  [[ $STATE_DIR = /* && $OUTPUT = /* ]] || fail "P014_DOCKER_ROLLBACK_PATH_NOT_ABSOLUTE"
  [[ -x $HOST_GATE ]] || fail "P014_DOCKER_ROLLBACK_HOST_GATE_INVALID"
  [[ -d $STATE_DIR && -f $STATE_DIR/install-started && -f $STATE_DIR/pre-docker.json ]] ||
    fail "P014_DOCKER_ROLLBACK_STATE_INVALID"
  [[ -f $STATE_DIR/rollback-armed && ! -e $STATE_DIR/install-complete ]] ||
    fail "P014_DOCKER_ROLLBACK_NOT_ARMED"
  [[ ! -e $OUTPUT ]] || fail "P014_DOCKER_ROLLBACK_OUTPUT_EXISTS"
  [[ ! -e $STATE_DIR/rollback-complete ]] || fail "P014_DOCKER_ROLLBACK_ALREADY_COMPLETE"
  [[ -f $STATE_DIR/runtime-roots-owned ]] ||
    fail "P014_DOCKER_ROLLBACK_RUNTIME_OWNERSHIP_MISSING"
  local command
  for command in \
    apt-get awk dpkg dpkg-query ip6tables-restore ip6tables-save \
    iptables-restore iptables-save mv nft pgrep python3 rm rmdir sha256sum sysctl systemctl; do
    command -v "$command" >/dev/null || fail "P014_DOCKER_ROLLBACK_COMMAND_MISSING:$command"
  done

  # Validate every destructive input before changing packages, files, services, or rules.
  local forwarding_values
  if ! forwarding_values=$(validate_rollback_preflight "$STATE_DIR/pre-docker.json"); then
    return 1
  fi
  local ipv4_forward
  local ipv6_forward
  read -r ipv4_forward ipv6_forward <<< "$forwarding_values"
  [[ $ipv4_forward =~ ^[01]$ && $ipv6_forward =~ ^[01]$ ]] ||
    fail "P014_DOCKER_ROLLBACK_FORWARDING_INVALID"
  validate_firewall_evidence "$STATE_DIR/pre-docker.json" "$STATE_DIR"

  verify_owned_final_path key-owned "$STATE_DIR/docker-key.sha256" "$DOCKER_KEY"
  verify_owned_final_path source-owned "$STATE_DIR/docker-source.sha256" "$DOCKER_SOURCE"

  local -a packages=()
  local package
  local status
  if [[ -f $STATE_DIR/installed-packages.txt ]]; then
    while IFS='=' read -r package _version; do
      [[ $package =~ $PACKAGE_ALLOWLIST ]] ||
        fail "P014_DOCKER_ROLLBACK_PACKAGE_OUTSIDE_ALLOWLIST"
    done < "$STATE_DIR/installed-packages.txt"
  fi
  for package in "${PACKAGE_NAMES[@]}"; do
    status=$(query_package_status "$package")
    if [[ $status != not-installed ]]; then
      packages+=("$package")
    fi
  done

  local runtime_evidence=0
  local unit_presence
  if ! unit_presence=$(runtime_units_presence); then
    return 1
  fi
  if ((${#packages[@]})) || command -v docker >/dev/null || [[ -e /var/lib/docker ]] ||
    [[ -e /var/lib/containerd ]] || [[ $unit_presence -eq 1 ]]; then
    runtime_evidence=1
  fi
  if [[ $runtime_evidence -eq 1 ]]; then
    inspect_owned_runtime_before_cleanup "$STATE_DIR"
  fi

  stop_runtime_units
  prove_runtime_stopped

  if ((${#packages[@]})); then
    if ! apt-get purge -y "${packages[@]}"; then
      dpkg --purge --force-remove-reinstreq "${packages[@]}"
    fi
  fi
  for package in "${PACKAGE_NAMES[@]}"; do
    status=$(query_package_status "$package")
    [[ $status == not-installed ]] ||
      fail "P014_DOCKER_ROLLBACK_PACKAGE_REMAINS:$package:$status"
  done
  systemctl daemon-reload
  prove_runtime_stopped

  # Close the verification-to-deletion window for final repository files.
  verify_owned_final_path key-owned "$STATE_DIR/docker-key.sha256" "$DOCKER_KEY"
  verify_owned_final_path source-owned "$STATE_DIR/docker-source.sha256" "$DOCKER_SOURCE"

  if [[ -f $STATE_DIR/source-owned ]]; then
    rm -f -- "$DOCKER_SOURCE" "$DOCKER_SOURCE_STAGE"
    touch "$STATE_DIR/source-removed"
  fi
  if [[ -f $STATE_DIR/key-owned ]]; then
    rm -f -- "$DOCKER_KEY" "$DOCKER_KEY_STAGE"
    touch "$STATE_DIR/key-removed"
  fi
  if [[ -f $STATE_DIR/keyring-dir-owned ]]; then
    rmdir -- "$KEYRING_DIR"
    touch "$STATE_DIR/keyring-dir-removed"
  fi

  # install-complete is forbidden above; these roots were absent before this armed transaction.
  rm -rf --one-file-system -- /var/lib/docker /var/lib/containerd
  touch "$STATE_DIR/runtime-roots-removed"

  restore_firewall_snapshot
  sysctl -q -w "net.ipv4.ip_forward=$ipv4_forward"
  sysctl -q -w "net.ipv6.conf.all.forwarding=$ipv6_forward"
  systemctl daemon-reload

  python3 "$HOST_GATE" post-rollback \
    --baseline "$STATE_DIR/pre-docker.json" \
    --output "$OUTPUT" \
    --samples 20

  touch "$STATE_DIR/rollback-complete"
  rm -f -- "$STATE_DIR/rollback-armed"
  echo "p014-docker-rollback-ok"
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  main "$@"
fi
