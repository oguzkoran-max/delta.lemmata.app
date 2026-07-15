# P014 Target-Host Read-Only Preflight

## Scope

This record captures a point-in-time, content-free inventory of the intended
shared VPS and a pre-change Lemmata health and latency baseline. The observation
ran against source commit
`dea9e67154d75852c5d69db9871fd4a1868bc236` after pull-request CI run
`29424064991` passed both `verify` and `container` jobs.

The run was deliberately read-only. It did not install a package, create swap,
start or stop a service, edit Caddy, alter DNS, pull an image, create a Delta
directory, or change Lemmata. No environment, credential, uploaded text, process
command line, or Caddyfile content was printed.

## Outcome

The target-host preflight stopped before any host change with exit code `21`.
The immediate fail-closed reason was `container_runtime_absent`: Docker, Podman,
containerd, and nerdctl were all absent, so the canonically tested P014 container
package cannot run on the observed host as it stands.

This is an expected safety outcome, not a Delta calculation or Lemmata failure.
Lemmata was active and healthy, Caddy was active, and the planned Delta loopback
port `8502` was free.

P014-AC-08 therefore remains `pending`. This record proves that the required
inventory was attempted without changing the live service and identifies the
blocking host prerequisite. It does not prove an accepted installation baseline.

## Observed Host

The retained observation began at `2026-07-15T14:47:45Z`; host values were read
at `2026-07-15T14:47:47Z`.

| Observation | Value |
| --- | ---: |
| Operating system | Ubuntu 26.04 LTS |
| Architecture | x86_64 |
| Kernel | 7.0.0-22-generic |
| CPUs | 2 |
| Total memory | 3,814 MiB |
| Used memory | 1,454 MiB |
| Available memory | 2,360 MiB |
| Swap | 0 MiB |
| Root disk | 38,114 MiB total; 32,621 MiB available; 11% used |
| Docker data root | absent |
| Container runtimes | Docker, Podman, containerd, and nerdctl absent |
| Caddy | active |
| Lemmata | active/running |
| Lemmata start | 2026-07-04 08:54:24 UTC |
| Lemmata memory | 1,118,232,576 bytes |
| Lemmata tasks | 16 |
| Lemmata resource caps | no finite `MemoryHigh`, `MemoryMax`, or CPU quota |
| Lemmata working directory | `/opt/lemmata` |
| Lemmata application port | `127.0.0.1:8501` listening |
| Planned Delta gateway port | `127.0.0.1:8502` free |
| Caddyfile SHA-256 | `ec824143747f51a2b571de61ae87bf06714e7be76684d5d9e665bb653116c9e5` |
| Public Lemmata health | `ok` |

Disk space is not the observed blocker. Memory headroom is not yet accepted:
the host has no swap, the existing Lemmata process is uncapped and uses about
1.04 GiB, and the validated Delta application profile alone permits up to
1,536 MiB before gateway and container-runtime overhead. Installing a runtime
and applying bounded load on this host therefore requires a separately approved
capacity plan and a repeated preflight. This record does not infer safety from
idle memory alone.

## Lemmata Baseline

Twenty sequential HTTPS health requests were made from the operator workstation
beginning at `2026-07-15T14:47:47Z`. All 20 returned HTTP `200`.

| Metric | Value |
| --- | ---: |
| Samples | 20 |
| HTTP 200 | 20 |
| Minimum | 166.34 ms |
| Median | 182.02 ms |
| Mean | 206.21 ms |
| p95, nearest-rank | 267.73 ms |
| Maximum | 268.60 ms |

Retained samples, in collection order:

```text
1 200 0.182156
2 200 0.254161
3 200 0.177580
4 200 0.259695
5 200 0.177556
6 200 0.171904
7 200 0.234677
8 200 0.177301
9 200 0.219066
10 200 0.177618
11 200 0.255953
12 200 0.166344
13 200 0.175160
14 200 0.267729
15 200 0.180909
16 200 0.240084
17 200 0.172697
18 200 0.268596
19 200 0.183163
20 200 0.181878
```

This small sequential sample is a pre-change operational reference. It is not a
performance benchmark, service-level objective, concurrency test, or proof that
Delta and Lemmata can coexist under load.

## Retained Gate Transcript

The SSH credential path and credential value are intentionally omitted. The
remote command set consisted only of `date`, OS/kernel/CPU/memory/disk reads,
runtime presence checks, safe `systemctl is-active` and selected `systemctl show`
properties, socket-state reads, a Caddyfile hash, and the public Lemmata health
request. The local latency command used system `curl`, discarded response bodies,
and retained only sample number, HTTP status, and elapsed time.

```text
started_at_utc=2026-07-15T14:47:45Z
host_observed_at_utc=2026-07-15T14:47:47Z
os=Ubuntu 26.04 LTS
architecture=x86_64
kernel=7.0.0-22-generic
cpu_count=2
memory_total_mib=3814
memory_used_mib=1454
memory_available_mib=2360
swap_total_mib=0
root_disk_total_mib=38114
root_disk_used_mib=3882
root_disk_available_mib=32621
root_disk_use_percent=11%
docker_data_root=absent
runtime_docker=absent
runtime_podman=absent
runtime_containerd=absent
runtime_nerdctl=absent
service_docker=inactive
service_caddy=active
service_lemmata=active
ActiveState=active
SubState=running
MainPID=3467
ExecMainStartTimestamp=Sat 2026-07-04 08:54:24 UTC
MemoryCurrent=1118232576
TasksCurrent=16
CPUQuotaPerSecUSec=infinity
MemoryHigh=infinity
MemoryMax=infinity
WorkingDirectory=/opt/lemmata
User=
Group=
PrivateTmp=no
port_8501=listening
port_8502=free
caddyfile_sha256=ec824143747f51a2b571de61ae87bf06714e7be76684d5d9e665bb653116c9e5
lemmata_health=ok
gate_failure=container_runtime_absent
preflight_gate=stopped_before_host_change
remote_gate_exit_code=21
latency_observed_at_utc=2026-07-15T14:47:47Z
latency_samples=20
latency_http_200=20
latency_min_ms=166.34
latency_median_ms=182.02
latency_p95_ms=267.73
latency_max_ms=268.60
latency_mean_ms=206.21
ended_at_utc=2026-07-15T14:47:52Z
```

## Gate Decision

The runbook requires a failed preflight to stop the rollout rather than work
around the missing prerequisite. The next permissible repository operations are:

1. Merge the exact green source and publication workflow through the normal PR.
2. Publish the exact green application image from the default branch and record
   its immutable registry manifest digest.
3. Make and record an explicit host-capacity decision before any live change.
4. If the existing VPS remains the target, prepare a rollback-backed container
   runtime and capacity procedure, then repeat this read-only preflight before
   installing Delta.

No Caddy, DNS, Delta service, or public activation step is authorized by this
record.

## Claim Boundary

This evidence supports a point-in-time target-host inventory, a healthy
pre-change Lemmata observation, an unused Delta port, and a transparent
fail-closed deployment decision. It does not establish target-host readiness,
container isolation, sufficient load headroom, live Delta health, live TLS,
Delta-Lemmata coexistence, restart cleanup, rollback, owner acceptance,
production maturity, complete FAIR compliance, or publication readiness.
