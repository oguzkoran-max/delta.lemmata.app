# P014 Start Prompt: Isolated Public-Alpha Deployment

## Instruction

Continue Delta from the verified P009 owner-walkthrough preparation commit
`147813c7c492fe82eb4a6a78e55e80a0ea10f058` on branch
`codex/p014-public-alpha-deploy`. Build the minimum P014 public-alpha deployment
slice locally, schema-first and tests-first, before making any change to the
shared VPS or `lda.lemmata.app`.

## Isolation Boundary

- Delta receives a separate container/service identity, loopback port,
  environment, secrets, writable runtime storage, network, and resource budget.
- No Delta artifact may read, mount, import, restart, reconfigure, or reuse a
  Lemmata secret, environment, volume, process, service, application directory,
  or internal port.
- The existing host Caddy service remains the TLS boundary. Only a narrow,
  independently reversible `delta.lemmata.app` route may be added after local
  validation and read-only host inventory.
- The public application and scientific worker run without runtime AI,
  analytics, login, permanent project storage, or unrestricted egress.
- The interface visibly says `Public alpha` and `experimental` without implying
  scientific validation, FAIR certification, production-grade isolation,
  demonstrated usability, or publication readiness.

## Minimum Local Package

1. A production runtime image that starts Streamlit on an internal port as a
   fixed non-root user and exposes a content-free health check.
2. An isolated deployment definition with read-only root filesystems, private
   temporary storage, dropped capabilities, no-new-privileges, CPU/RAM/PID
   limits, bounded restart behavior, and no direct public bind.
3. A separate gateway boundary that binds only to host loopback port `8502`,
   enforces strict Host, request-size, rate, connection, timeout, and security
   header policy, and supports Streamlit WebSocket traffic.
4. Three distinct generated runtime secrets, a production environment template,
   installation checks, health checks, rollback steps, and two-site smoke steps.
5. Fail-closed validators and CI gates that inspect the built runtime, non-root
   identity, health, filesystem, limits, labels, and public-alpha copy.

## Evidence Boundary

- Local validation proves only that the deployment package is internally
  consistent and that its container controls behave in CI.
- Shared-VPS isolation, real TLS/Host routing, load behavior, reboot cleanup,
  Lemmata coexistence, and rollback become evidence only after exact commands,
  outputs, timestamps, and artifact digests are recorded on the target host.
- Full CE-14 and CE-15 claims remain locked after minimum-alpha activation.
- Failed builds, failed health checks, and failed rollout attempts are retained
  with their causes; no evidence is rewritten to create a clean history.

## Stop Conditions

Stop and record the blocker instead of activating when:

- the exact image cannot be identified by immutable digest;
- any required secret is absent, shared, weak, or committed;
- Delta needs access to a Lemmata path, environment, volume, service, or secret;
- the gateway cannot enforce strict Host, body-size, rate, timeout, and WebSocket
  behavior without changing Lemmata's runtime;
- a Delta load or restart causes a Lemmata error, restart, or unacceptable
  latency increase;
- health, cleanup, rollback, or both-site smoke checks fail;
- meeting the date would require disabling XSRF/CORS, widening egress, removing
  resource limits, or weakening P003-P009 validation and privacy controls.
