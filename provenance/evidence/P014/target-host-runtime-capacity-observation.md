# P014 Target-Host Runtime and Capacity Observation

## Scope

This record extends the first read-only P014 preflight with the host facts needed
to choose a container runtime and capacity policy. It observed the intended
shared VPS at `2026-07-15T15:54:34Z` while the repository `main` commit was
`cc44132b524ae31e052a3af69ad4c416c88a223c`.

The command was read-only. It did not install or remove a package, add an apt
source or key, create swap, change forwarding or firewall rules, start or stop a
service, pull an image, create a Delta path, edit Caddy or DNS, or alter Lemmata.
No environment, credential, process command line, uploaded text, or Caddyfile
content was read or retained.

## Outcome

The observation succeeded and leaves P014-AC-08 pending. The host is technically
compatible with the canonically tested cgroup resource controls, and Docker's
official documentation lists its operating system and architecture as supported.
However, runtime installation would change the host firewall/forwarding state,
and the memory margin remains narrow enough to require an explicit owner decision
and measured fail-closed load gate.

Lemmata remained active and healthy with zero recorded restarts. Port `8502`
remained free. No host modification was made.

## Content-Free Observation

| Observation | Value |
| --- | ---: |
| Operating system | Ubuntu 26.04 |
| Architecture | x86_64 |
| Virtualization | KVM |
| CPUs | 2 |
| Total memory | 3,814 MiB |
| Available memory | 2,357 MiB |
| Swap | 0 MiB |
| Root disk available | 32,621 MiB |
| Root filesystem | ext4 |
| Cgroup filesystem | cgroup v2 |
| Required controllers | `cpu`, `memory`, and `pids` present |
| UFW service unit | active |
| UFW policy state | inactive |
| firewalld | inactive |
| iptables | v1.8.11 using nf_tables |
| nftables | v1.1.6 |
| nftables rule lines | 0 |
| iptables rule lines | 0 |
| ip6tables rule lines | 0 |
| IPv4 forwarding | disabled |
| IPv6 forwarding | disabled |
| Host interfaces | 2, including loopback |
| Conflicting Docker packages | 0 |
| Existing Docker apt-source files | 0 |
| Existing Docker apt-key files | 0 |
| Caddy | active |
| Lemmata | active and healthy |
| Lemmata restart count | 0 |
| Lemmata memory | 1,118,232,576 bytes |
| Lemmata port `8501` | listening |
| Delta port `8502` | free |
| Memory PSI, `some` avg10/60/300 | 0.00 / 0.00 / 0.00 |
| Memory PSI, `full` avg10/60/300 | 0.00 / 0.00 / 0.00 |

The UFW systemd unit being active does not mean the firewall policy is enabled;
the safe status query returned `Status: inactive`. The three empty rule counts
are a pre-Docker baseline. Docker is expected to change this state for bridge
networking, so the differences must be captured and verified rather than treated
as invisible package-installation detail.

## Capacity Interpretation

The observed available memory minus the two fixed Delta container ceilings is:

```text
2,357 MiB - 1,536 MiB - 128 MiB = 693 MiB
```

This is not a forecast of actual consumption and does not include all daemon or
host variation. It shows why the idle snapshot cannot itself establish safe
coexistence. Delta's `memswap_limit` equals its `mem_limit` for both containers;
the Docker Compose specification states that this equality denies container
swap. The host currently has no swap in any case.

The project had already frozen a provisional CE-15 shared-host budget of no more
than `20%` Lemmata p95 latency increase, with zero Lemmata error and restart. The
candidate host plan retains that threshold and adds explicit free-memory, OOM,
memory-pressure, socket, and firewall checks. No capacity or isolation claim is
made before those tests pass.

## Official Documentation Check

Official Docker documentation retrieved on 2026-07-15 states that:

- Ubuntu Resolute 26.04 LTS and x86_64 are supported by Docker Engine;
- Docker creates firewall rules for Linux bridge networks and may enable IP
  forwarding;
- disabling Docker's firewall management is not appropriate for most users and
  can break container networking;
- when `memswap_limit` equals `mem_limit`, the container cannot use swap.

Official GitHub Container Registry documentation states that pulling a private
package requires a classic personal access token with at least `read:packages`.
The future pull therefore requires a dedicated least-privilege credential that
is supplied through standard input, followed by logout; no token may be retained
in repository evidence.

Sources:

- <https://docs.docker.com/engine/install/ubuntu/>
- <https://docs.docker.com/engine/network/packet-filtering-firewalls/>
- <https://docs.docker.com/reference/compose-file/services/#memswap_limit>
- <https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry>

## Retained Transcript

```text
started_at_utc=2026-07-15T15:54:34Z
os=Ubuntu 26.04
architecture=x86_64
virt=kvm
cpu_count=2
memory_total_mib=3814
memory_available_mib=2357
swap_total_mib=0
root_disk_available_mib=32621
root_fs=ext4
cgroup_fs=cgroup2
cgroup_controllers=cpuset cpu io memory hugetlb pids rdma misc dmem
ufw_service=active
ufw_status=Status: inactive
firewalld_service=inactive
iptables_version=iptables v1.8.11 (nf_tables)
nft_version=nftables v1.1.6
nft_ruleset_lines=0
iptables_save_lines=0
ip6tables_save_lines=0
ipv4_forward=0
ipv6_forward=0
interface_count=2
conflicting_package_count=0
docker_source_files=0
docker_key_files=0
lemmata_active=active
lemmata_restart_count=0
lemmata_memory_bytes=1118232576
caddy_active=active
lemmata_health=ok
port_8501=listening
port_8502=free
memory_psi=some avg10=0.00 avg60=0.00 avg300=0.00 total=2104360;full avg10=0.00 avg60=0.00 avg300=0.00 total=2097739;
ended_at_utc=2026-07-15T15:54:34Z
```

The exact SSH destination, credential, and local credential path are not
retained. Replay requires separately authorized operator access.

## Decision Boundary

The evidence supports a proposed same-VPS, official-Docker, no-new-swap
preparation path with strict fail-closed gates. It does not authorize that path.
It does not prove accepted host readiness, sufficient capacity, firewall safety
after Docker starts, private-registry pull access, Delta installation, live TLS,
coexistence under load, rollback, owner acceptance, FAIR certification, complete
isolation, or publication readiness.
