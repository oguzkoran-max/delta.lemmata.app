# P016 ADR Proposal: Narrative Surface Routing (DRAFT — owner decision required)

Status: Proposal only. No production routing, DNS, Caddy, nginx, container, or
Streamlit change is made by P016. The historical P002/P004 decision (direct
workbench at root, no marketing landing) remains in force until the owner
explicitly decides otherwise.

## Context
The prototype is a static, dependency-free page. The live chain is
Caddy (TLS, delta.lemmata.app) → nginx gateway (127.0.0.1:8502) → Streamlit.
Verified constraint from the 2026-07-19 deployment session: nginx
`worker_connections 128` and upstream `keepalive 4` exhausted under a single
aggressive client, returning 502s on Streamlit JS chunks (session handoff,
commit 38eafeb). **Any added public surface makes raising gateway capacity a production
prerequisite — and the fix must travel through BOTH layers: nginx
`worker_connections` AND the compose service's `nofile` ulimit (currently the
binding cap), shipped as a new release.**

## Option A — root narrative + app.delta.lemmata.app workbench
+ Streamlit stays at a path-root (no baseUrlPath work); clean separation.
− New DNS record + TLS cert; canonical-URL choice; cross-host nav + CSP review;
  the Caddy→nginx gateway chain is host-pinned (`Host delta.lemmata.app`
  header_up + strict host checks) and must be reconfigured for the new app host;
  second health/monitoring surface; every existing deep link and the published
  alpha URL changes meaning → migration comms + redirects; rollback = DNS-scoped.
Risk class: medium-high, mostly operational.

## Option B — root narrative + delta.lemmata.app/workbench/
+ One host, one cert, brandable root.
− Streamlit `server.baseUrlPath` must be set and *proven* for: /_stcore/health,
  /_stcore/stream WebSocket upgrade through Caddy+nginx, JS/CSS chunk paths,
  uploads/downloads (XSRF origin checks), trailing-slash redirects, old URLs.
  The 2026-07-19 chunk-502 incident shows this chain is already capacity-tight;
  nginx's rate-limit zones are anchored to `^/static/` and would need re-scoping
  under a `/workbench/` prefix; path rewiring multiplies failure modes. Rollback requires config + image
  coordination.
Risk class: highest.

## Option C — workbench stays at root; narrative at /how-delta-works/ (or preview host)
+ Preserves the accepted direct-workbench contract verbatim; zero Streamlit
  change; Caddy `handle_path /how-delta-works/*` serves the static files
  directly (bypassing nginx) **plus an explicit `redir /how-delta-works
  /how-delta-works/ 308`** so the slashless URL cannot fall through to the
  workbench; trivially rollbackable (remove one route); lets the owner
  user-test the narrative before any identity decision.
− Narrative is less prominent (linked from workbench header/footer and shareable
  directly).
Risk class: lowest.

## Recommendation
Adopt **Option C now** (single Caddy `handle_path /how-delta-works/*` serving the
static prototype directory, plus a small "How Delta works" link in the workbench
header), with **Option A as the candidate end-state** if the owner later decides
the narrative should own the root. Precondition for either: gateway capacity fix
(nginx `worker_connections` ≥1024 with a matching compose `nofile` ulimit raise;
upstream keepalive is a reuse optimisation, not the exhaustion cap) shipped as
its own release. Option B is
not recommended.

## Exact owner decisions required before any integration
1. Record HD + Run for the 2026-07-19 production deployment (retroactive
   bookkeeping of an explicit chat decision) — independent of P016.
2. Approve/reject Option C publication of the narrative (with URL choice).
3. Approve the gateway-capacity release as prerequisite.
4. Decide whether "Open the workbench" on the narrative points to root (C) or a
   future app subdomain (A).
5. Optional: approve one Higgsfield style frame (credits) — otherwise the page
   ships fully code-native.

## Rollback plan (Option C)
Remove the Caddy route + header link commit; static directory remains in repo;
no data, science, or workbench behaviour is touched. Verified by re-running the
live health checks and the workbench browser gate.
