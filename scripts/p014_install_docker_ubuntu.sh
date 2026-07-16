#!/usr/bin/env bash
set -Eeuo pipefail

umask 077
export DEBIAN_FRONTEND=noninteractive
export LC_ALL=C
unset APT_CONFIG

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
HOST_GATE="$SCRIPT_DIR/p014_host_gate.py"
ROLLBACK="$SCRIPT_DIR/p014_rollback_docker_ubuntu.sh"
KEYRING_DIR=/etc/apt/keyrings
DOCKER_KEY=$KEYRING_DIR/docker.asc
DOCKER_KEY_STAGE=$KEYRING_DIR/.docker.asc.p014
DOCKER_SOURCE=/etc/apt/sources.list.d/docker.sources
DOCKER_SOURCE_STAGE=/etc/apt/sources.list.d/.docker.sources.p014
DOCKER_REPOSITORY_URL=https://download.docker.com/linux/ubuntu
EXPECTED_FINGERPRINT=9DC858229FC7DD38854AE2D88D81803C0EBFCD88
PACKAGES=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
CONFLICTING_PACKAGES=(
  docker.io
  docker-compose
  docker-compose-v2
  docker-doc
  podman-docker
  containerd
  runc
  docker-ce-rootless-extras
)
APT_OPTIONS=()
PRE_FLIGHT=
POST_OUTPUT=
ROLLBACK_OUTPUT=
STATE_DIR=
APPLY=0
TRANSACTION_ACTIVE=0

usage() {
  echo "usage: $0 --preflight PATH --post-output PATH --rollback-output PATH --state-dir PATH --apply" >&2
  exit 2
}

fail() {
  echo "$1" >&2
  return 1
}

validate_gate_evidence() {
  local path=$1
  local expected_phase=$2
  python3 - "$path" "$expected_phase" <<'PY'
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
expected_phase = sys.argv[2]
try:
    info = os.stat(path)
    with open(path, encoding="utf-8") as handle:
        value = json.load(handle, parse_constant=reject_constant)
except (OSError, TypeError, ValueError, json.JSONDecodeError):
    fail("P014_DOCKER_INSTALL_GATE_EVIDENCE_INVALID")

if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
    fail("P014_DOCKER_INSTALL_GATE_EVIDENCE_PERMISSIONS_INVALID")
if not isinstance(value, dict):
    fail("P014_DOCKER_INSTALL_GATE_EVIDENCE_INVALID")
if value.get("schema_version") != "1.3.0":
    fail("P014_DOCKER_INSTALL_GATE_SCHEMA_INVALID")
if value.get("capture_mode") != "live" or value.get("phase") != expected_phase:
    fail("P014_DOCKER_INSTALL_GATE_PHASE_INVALID")
if value.get("gate") != {"passed": True, "failures": []}:
    fail("P014_DOCKER_INSTALL_GATE_NOT_ACCEPTED")
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
    fail("P014_DOCKER_INSTALL_FIREWALL_EVIDENCE_INVALID")

for name, path in names.items():
    try:
        payload = path.read_bytes()
        text = payload.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        fail(f"P014_DOCKER_INSTALL_FIREWALL_CAPTURE_INVALID:{name}")
    observed = {
        "line_count": sum(bool(line.strip()) for line in text.splitlines()),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    if observed != expected.get(name):
        fail(f"P014_DOCKER_INSTALL_FIREWALL_CAPTURE_MISMATCH:{name}")
PY
}

validate_downloaded_keyring() {
  local key_path=$1
  local colon_evidence=$2
  if ! gpg --batch --show-keys --with-colons "$key_path" > "$colon_evidence"; then
    fail "P014_DOCKER_INSTALL_KEY_INSPECTION_FAILED"
    return 1
  fi
  python3 - "$colon_evidence" "$EXPECTED_FINGERPRINT" <<'PY'
import pathlib
import re
import sys


def fail(code):
    print(code, file=sys.stderr)
    raise SystemExit(1)


try:
    lines = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
except (OSError, UnicodeDecodeError):
    fail("P014_DOCKER_INSTALL_KEY_EVIDENCE_INVALID")

primary_fingerprints = []
awaiting_primary_fingerprint = False
for line in lines:
    fields = line.split(":")
    record_type = fields[0] if fields else ""
    if record_type == "pub":
        primary_fingerprints.append(None)
        awaiting_primary_fingerprint = True
    elif record_type == "sub":
        awaiting_primary_fingerprint = False
    elif record_type == "fpr" and awaiting_primary_fingerprint:
        if len(fields) <= 9 or primary_fingerprints[-1] is not None:
            fail("P014_DOCKER_INSTALL_KEY_PRIMARY_FINGERPRINT_INVALID")
        primary_fingerprints[-1] = fields[9]
        awaiting_primary_fingerprint = False

expected = sys.argv[2]
if (
    len(primary_fingerprints) != 1
    or primary_fingerprints[0] != expected
    or re.fullmatch(r"[0-9A-F]{40}", primary_fingerprints[0] or "") is None
):
    fail("P014_DOCKER_INSTALL_KEY_PRIMARY_SET_INVALID")
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
  fail "P014_DOCKER_INSTALL_PACKAGE_QUERY_FAILED:$package"
}

configure_isolated_apt() {
  local evidence_root=$1
  local list_root=$evidence_root/apt-lists
  local archive_root=$evidence_root/apt-archives
  install -d -o root -g root -m 0700 "$list_root" "$list_root/partial"
  install -d -o root -g root -m 0700 "$archive_root" "$archive_root/partial"
  APT_OPTIONS=(
    -o "Dir::Etc::sourcelist=$DOCKER_SOURCE"
    -o 'Dir::Etc::sourceparts=-'
    -o "Dir::State::lists=$list_root"
    -o "Dir::Cache::archives=$archive_root"
    -o 'APT::Install-Recommends=false'
    -o 'APT::Install-Suggests=false'
    -o 'APT::Get::List-Cleanup=false'
  )
}

isolated_apt_update() {
  apt-get "${APT_OPTIONS[@]}" update
}

isolated_apt_policy() {
  apt-cache "${APT_OPTIONS[@]}" policy "$1"
}

isolated_apt_install() {
  apt-get "${APT_OPTIONS[@]}" install -y --no-install-recommends "$@"
}

isolated_apt_simulate_install() {
  apt-get "${APT_OPTIONS[@]}" --simulate install -y --no-install-recommends "$@"
}

validate_apt_simulation() {
  local simulation_path=$1
  python3 - "$simulation_path" "${PACKAGES[@]}" <<'PY'
import pathlib
import sys


def fail(code):
    print(code, file=sys.stderr)
    raise SystemExit(1)


try:
    lines = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
except (OSError, UnicodeDecodeError):
    fail("P014_DOCKER_INSTALL_SIMULATION_EVIDENCE_INVALID")

allowed = set(sys.argv[2:])
introduced = []
for line in lines:
    fields = line.split()
    if not fields:
        continue
    if fields[0] == "Remv":
        fail("P014_DOCKER_INSTALL_SIMULATION_REMOVAL_PROPOSED")
    if fields[0] != "Inst":
        continue
    if len(fields) < 2:
        fail("P014_DOCKER_INSTALL_SIMULATION_PARSE_FAILED")
    introduced.append(fields[1].split(":", maxsplit=1)[0])

if len(introduced) != len(allowed) or set(introduced) != allowed:
    fail("P014_DOCKER_INSTALL_SIMULATION_PACKAGE_SET_INVALID")
PY
}

require_docker_runtime_empty() {
  local image_ids
  local container_ids
  if ! image_ids=$(docker image ls --all --quiet); then
    fail "P014_DOCKER_INSTALL_IMAGE_INSPECTION_FAILED"
    return 1
  fi
  if [[ -n ${image_ids//[[:space:]]/} ]]; then
    fail "P014_DOCKER_INSTALL_IMAGE_PRESENT"
    return 1
  fi
  if ! container_ids=$(docker container ls --all --quiet); then
    fail "P014_DOCKER_INSTALL_CONTAINER_INSPECTION_FAILED"
    return 1
  fi
  if [[ -n ${container_ids//[[:space:]]/} ]]; then
    fail "P014_DOCKER_INSTALL_CONTAINER_PRESENT"
    return 1
  fi
}

handle_install_failure() {
  local status=$1
  local reason=$2
  trap - ERR INT TERM
  if [[ $TRANSACTION_ACTIVE -eq 1 ]]; then
    echo "p014-docker-install-failed:$reason; starting deterministic rollback" >&2
    if ! "$ROLLBACK" --state-dir "$STATE_DIR" --output "$ROLLBACK_OUTPUT" --apply; then
      echo "P014_DOCKER_AUTOMATIC_ROLLBACK_FAILED" >&2
    fi
  fi
  exit "$status"
}

handle_install_error() {
  local status=$1
  handle_install_failure "$status" ERR
}

handle_install_signal() {
  local signal_name=$1
  case "$signal_name" in
    INT) handle_install_failure 130 INT ;;
    TERM) handle_install_failure 143 TERM ;;
    *) handle_install_failure 1 "UNKNOWN_SIGNAL:$signal_name" ;;
  esac
}

main() {
  while (($#)); do
    case "$1" in
      --preflight) PRE_FLIGHT=${2:-}; shift 2 ;;
      --post-output) POST_OUTPUT=${2:-}; shift 2 ;;
      --rollback-output) ROLLBACK_OUTPUT=${2:-}; shift 2 ;;
      --state-dir) STATE_DIR=${2:-}; shift 2 ;;
      --apply) APPLY=1; shift ;;
      *) usage ;;
    esac
  done

  [[ $APPLY -eq 1 ]] || usage
  [[ $EUID -eq 0 ]] || fail "P014_DOCKER_INSTALL_REQUIRES_ROOT"
  [[ $PRE_FLIGHT = /* && $POST_OUTPUT = /* && $ROLLBACK_OUTPUT = /* && $STATE_DIR = /* ]] ||
    fail "P014_DOCKER_INSTALL_PATH_NOT_ABSOLUTE"
  [[ -x $HOST_GATE && -x $ROLLBACK ]] || fail "P014_DOCKER_INSTALL_HELPER_INVALID"
  [[ -f $PRE_FLIGHT && ! -e $POST_OUTPUT && ! -e $ROLLBACK_OUTPUT && ! -e $STATE_DIR ]] ||
    fail "P014_DOCKER_INSTALL_PATH_STATE_INVALID"
  command -v python3 >/dev/null || fail "P014_DOCKER_INSTALL_COMMAND_MISSING:python3"
  validate_gate_evidence "$PRE_FLIGHT" pre-docker

  # This installer is intentionally narrow: it refuses to merge with an existing runtime.
  . /etc/os-release
  [[ ${ID:-} == ubuntu && ${VERSION_ID:-} == 26.04 ]] ||
    fail "P014_DOCKER_INSTALL_OS_UNSUPPORTED"
  [[ $(dpkg --print-architecture) == amd64 ]] || fail "P014_DOCKER_INSTALL_ARCH_UNSUPPORTED"
  local command
  for command in \
    apt-cache apt-get awk curl dpkg dpkg-query gpg install ip6tables-restore \
    ip6tables-save iptables-restore iptables-save mv nft python3 sha256sum systemctl; do
    command -v "$command" >/dev/null || fail "P014_DOCKER_INSTALL_COMMAND_MISSING:$command"
  done
  if command -v docker >/dev/null; then
    fail "P014_DOCKER_INSTALL_RUNTIME_ALREADY_PRESENT"
    return 1
  fi

  local package
  local status
  for package in "${PACKAGES[@]}" "${CONFLICTING_PACKAGES[@]}"; do
    status=$(query_package_status "$package")
    [[ $status == not-installed ]] ||
      fail "P014_DOCKER_INSTALL_CONFLICTING_PACKAGE:$package:$status"
  done
  [[ ! -e $DOCKER_KEY && ! -e $DOCKER_KEY_STAGE ]] ||
    fail "P014_DOCKER_INSTALL_PREEXISTING_KEY_STATE"
  [[ ! -e $DOCKER_SOURCE && ! -e $DOCKER_SOURCE_STAGE ]] ||
    fail "P014_DOCKER_INSTALL_PREEXISTING_SOURCE_STATE"
  [[ ! -e /var/lib/docker && ! -e /var/lib/containerd ]] ||
    fail "P014_DOCKER_INSTALL_PREEXISTING_RUNTIME_STATE"

  install -d -o root -g root -m 0700 "$STATE_DIR"
  install -o root -g root -m 0600 "$PRE_FLIGHT" "$STATE_DIR/pre-docker.json"

  # Preserve exact private firewall inputs and bind them to host-gate fingerprints.
  nft list ruleset > "$STATE_DIR/firewall-nftables.before"
  iptables-save > "$STATE_DIR/firewall-iptables.before"
  ip6tables-save > "$STATE_DIR/firewall-ip6tables.before"
  validate_firewall_evidence "$STATE_DIR/pre-docker.json" "$STATE_DIR"

  # Re-observe the live host immediately before any apt, key, source, or runtime mutation.
  python3 "$HOST_GATE" pre-mutation \
    --baseline "$STATE_DIR/pre-docker.json" \
    --output "$STATE_DIR/pre-mutation.json" \
    --samples 20
  validate_gate_evidence "$STATE_DIR/pre-mutation.json" pre-mutation

  touch "$STATE_DIR/install-started"
  touch "$STATE_DIR/rollback-armed"
  touch "$STATE_DIR/runtime-roots-owned"
  trap 'handle_install_error $?' ERR
  trap 'handle_install_signal INT' INT
  trap 'handle_install_signal TERM' TERM
  TRANSACTION_ACTIVE=1

  if [[ ! -d $KEYRING_DIR ]]; then
    touch "$STATE_DIR/keyring-dir-owned"
    install -d -o root -g root -m 0755 "$KEYRING_DIR"
  fi
  curl --fail --silent --show-error --location \
    https://download.docker.com/linux/ubuntu/gpg \
    --output "$STATE_DIR/docker.asc.download"
  validate_downloaded_keyring \
    "$STATE_DIR/docker.asc.download" "$STATE_DIR/docker-key.colons"

  local key_sha256
  local actual_sha256
  key_sha256=$(sha256sum "$STATE_DIR/docker.asc.download" | awk '{print $1}')
  printf '%s  %s\n' "$key_sha256" "$DOCKER_KEY" > "$STATE_DIR/docker-key.sha256"
  touch "$STATE_DIR/key-owned"
  install -o root -g root -m 0644 "$STATE_DIR/docker.asc.download" "$DOCKER_KEY_STAGE"
  actual_sha256=$(sha256sum "$DOCKER_KEY_STAGE" | awk '{print $1}')
  [[ $actual_sha256 == "$key_sha256" ]] || fail "P014_DOCKER_INSTALL_KEY_STAGE_MISMATCH"
  mv -T "$DOCKER_KEY_STAGE" "$DOCKER_KEY"

  local architecture
  architecture=$(dpkg --print-architecture)
  printf '%s\n' \
    'Types: deb' \
    "URIs: $DOCKER_REPOSITORY_URL" \
    "Suites: ${VERSION_CODENAME}" \
    'Components: stable' \
    "Architectures: ${architecture}" \
    "Signed-By: ${DOCKER_KEY}" > "$STATE_DIR/docker.sources.desired"
  local source_sha256
  source_sha256=$(sha256sum "$STATE_DIR/docker.sources.desired" | awk '{print $1}')
  printf '%s  %s\n' "$source_sha256" "$DOCKER_SOURCE" > "$STATE_DIR/docker-source.sha256"
  touch "$STATE_DIR/source-owned"
  install -o root -g root -m 0644 "$STATE_DIR/docker.sources.desired" "$DOCKER_SOURCE_STAGE"
  actual_sha256=$(sha256sum "$DOCKER_SOURCE_STAGE" | awk '{print $1}')
  [[ $actual_sha256 == "$source_sha256" ]] ||
    fail "P014_DOCKER_INSTALL_SOURCE_STAGE_MISMATCH"
  mv -T "$DOCKER_SOURCE_STAGE" "$DOCKER_SOURCE"

  configure_isolated_apt "$STATE_DIR"
  isolated_apt_update
  local -a SPECS=()
  : > "$STATE_DIR/candidate-packages.txt"
  local candidate
  local policy
  for package in "${PACKAGES[@]}"; do
    if ! policy=$(isolated_apt_policy "$package"); then
      fail "P014_DOCKER_INSTALL_CANDIDATE_QUERY_FAILED:$package"
      return 1
    fi
    printf '%s\n' "$policy" > "$STATE_DIR/apt-policy-$package.txt"
    candidate=$(printf '%s\n' "$policy" | awk '/Candidate:/ {print $2; exit}')
    [[ -n $candidate && $candidate != '(none)' ]] ||
      fail "P014_DOCKER_INSTALL_CANDIDATE_MISSING:$package"
    [[ $policy == *"$DOCKER_REPOSITORY_URL"* && $policy == *'/stable'* ]] ||
      fail "P014_DOCKER_INSTALL_CANDIDATE_ORIGIN_INVALID:$package"
    printf '%s=%s\n' "$package" "$candidate" >> "$STATE_DIR/candidate-packages.txt"
    SPECS+=("$package=$candidate")
  done
  if ! isolated_apt_simulate_install "${SPECS[@]}" > "$STATE_DIR/apt-install.simulation"; then
    fail "P014_DOCKER_INSTALL_SIMULATION_FAILED"
    return 1
  fi
  validate_apt_simulation "$STATE_DIR/apt-install.simulation"
  touch "$STATE_DIR/package-mutation-authorized"
  isolated_apt_install "${SPECS[@]}"

  dpkg-query -W -f='${binary:Package}=${Version}\n' "${PACKAGES[@]}" \
    > "$STATE_DIR/installed-packages.txt"
  systemctl enable --now docker.service
  systemctl is-active --quiet docker.service
  docker version --format '{{.Server.Version}}' > "$STATE_DIR/docker-engine-version.txt"
  docker compose version --short > "$STATE_DIR/docker-compose-version.txt"
  require_docker_runtime_empty
  touch "$STATE_DIR/runtime-confirmed-empty"

  python3 "$HOST_GATE" post-docker \
    --baseline "$STATE_DIR/pre-docker.json" \
    --output "$POST_OUTPUT" \
    --samples 20

  touch "$STATE_DIR/install-complete"
  TRANSACTION_ACTIVE=0
  trap - ERR INT TERM
  rm -f -- "$STATE_DIR/rollback-armed"
  touch "$STATE_DIR/rollback-disarmed"
  echo "p014-docker-install-ok"
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  main "$@"
fi
