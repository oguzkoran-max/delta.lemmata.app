# P002 Acceptance Report

**Ticket:** P002

**Run date:** 2026-07-10

**Scope:** English-only Streamlit workbench shell, interface contracts, runtime boundary, responsive and keyboard evidence

**Scientific analysis:** Not implemented

## Result

All seven P002 acceptance criteria passed within their stated interface-shell
scope. Delta now opens directly as a workbench, exposes three research purposes,
shows Guided and Research modes, and reserves corpus, parameter, limitation, and
run evidence as first-class interface regions. Controls that depend on secure
ingestion or scientific computation remain disabled and explicitly labelled.
The implementation snapshot was then restored and verified from a new Git clone.

This result does not claim that upload is safe, `stylo` runs, any result is
scientifically valid, the service is production-secure, or the interface is
generally easy to learn.

## Interface Contract

- The first screen is the workbench, not a marketing landing page.
- The research purposes are Text Proximity, Group Comparison, and Style Over Time.
- Guided and Research are visible as distinct future workflow modes.
- All 90 user-facing strings are held in one English registry; no locale selector
  or Turkish/Italian interface is shipped in v0.1.
- Empty, loading, error, cancelled, and complete states share a versioned contract.
- Public build information is allowlisted and rejects path- or secret-shaped IDs.
- Runtime AI, analytics, login, permanent storage, and declared external endpoints
  are absent from the P002 runtime policy.

## Acceptance Evidence

| Gate | Result | Evidence |
|---|---|---|
| P002-AC-01 responsive shell | Passed | 1440x1000 and 390x844 screenshots; zero horizontal/text overflow or panel overlap in the recorded audits |
| P002-AC-02 keyboard and names | Passed with disclosed scope | ArrowRight and Space changed the selected research purpose; zero unnamed visible controls |
| P002-AC-03 copy boundaries | Passed | Central 90-string snapshot and automated denylist reported zero prohibited claims |
| P002-AC-04 egress-denied shell | Passed with disclosed scope | Shell loaded under outbound-network denial; zero external process sockets, DOM assets, AI, analytics, login, or remote-storage requests observed |
| P002-AC-05 English registry | Passed | One `en` catalog, 90 entries, no language selector, and tests preventing long copy duplication in app modules |
| P002-AC-06 public health | Passed | Version/build allowlist tests; path- and secret-shaped build ID becomes `invalid` |
| P002-AC-07 shared states | Passed | Five interface states and presentation keys covered by unit and shell tests |

## Automated Verification

Final `./scripts/verify.sh` result:

- Ruff format: passed
- Ruff lint: passed
- strict mypy: passed, 7 source files
- pytest: 40 passed
- measured Python source coverage: 100%
- metadata, provenance-record, repository, supply-chain, and R-lock checks: passed

The command emitted an inherited `requests` dependency warning from the host
Anaconda installation before the locked tool ran. It did not change the exit
status or the locked project environment.

## Clean-Clone Rerun

Commit `a888e7c81e5fdae12687903de29d0728f5c7cbd5` was cloned with local-object
sharing disabled. `./scripts/bootstrap.sh` restored the locked Python and R
environments. `./scripts/verify.sh` again passed 40 tests, 100% measured Python
source coverage, metadata and record validation, repository and supply-chain
checks, and the R lock gate. `git status --porcelain=v1` returned no versionable
changes after the rerun.

The rerun does not add browser, production, or scientific-computation claims; it
only demonstrates that the committed P002 source and automated checks restore in
a fresh local clone.

## Browser and Accessibility Observations

- Desktop: 1440x1000 CSS pixels, sidebar expanded.
- Mobile: 390x844 CSS pixels, sidebar collapsed off-canvas.
- No page-wide horizontal scroll, clipped text, incoherent panel overlap, external
  asset URL, or prohibited phrase was found at either accepted viewport.
- Keyboard selection moved from Text Proximity to Group Comparison and exposed the
  correct checked state.
- This is not a full WCAG audit. Screen-reader behavior and workflow error-focus
  handling remain open until executable workflows exist.

## Offline and Runtime Boundary

The shell was served on loopback under a macOS sandbox profile that denied outbound
network connections. The complete UI loaded with build marker
`P002-egress-denied`. Process observation showed only the local listening socket
and the browser's local connection. A DNS-resolved HTTPS negative control and a
direct-public-IP negative control were both blocked. Browser inspection found no
external DOM asset.

This is interface-shell evidence, not production isolation. Container egress,
reverse proxy, TLS, Host, CORS, CSRF, headers, and shared-VPS isolation remain P014
responsibilities.

## Failures Preserved

1. The first Ruff pass rejected long catalog lines. The strings were reflowed
   without changing their values.
2. The first dynamic-purpose test compared escaped HTML and missed an apostrophe.
   The test now decodes rendered HTML before assertion.
3. Browser inspection found a two-pixel overflow in the locked-corpus badge. The
   responsive column allocation was widened and retested.
4. A dynamically changed purpose heading retained Streamlit's stale anchor from
   the first purpose. It was replaced with an accessible HTML heading role.
5. A transparent Streamlit header improved continuity but produced a black layer
   in a high-density screenshot. The header was made opaque and content spacing
   was adjusted.
6. The first final verification run stopped because `webapp.py` required automatic
   formatting after the accessibility edit. Ruff formatted the file.
7. The second final verification run passed 40 tests at 100% coverage but the
   repository scan rejected a deliberate macOS home-directory negative-test literal. The
   test now constructs a generic absolute POSIX path without embedding a developer
   path pattern; the third full verification passed.
8. An initial mobile DOM audit treated the collapsed off-canvas sidebar as visible,
   causing false overflow and unnamed-control findings. The audit was corrected to
   require viewport intersection and was rerun; the accepted result is preserved in
   `browser-audit.json`.

## FAIR-Oriented Trace

- Human decisions: `HD-20260710-0003`, `HD-20260710-0004`
- Native request hash record: `PE-20260710-0002`
- Development ticket: `P002`
- Test run: `RUN-20260710-0003`
- Clean-clone rerun: `RUN-20260710-0004`
- Exact English copy snapshot: `copy-snapshot.txt`
- Browser geometry and visual evidence: `browser-audit.json` and two PNG files
- Keyboard evidence: `accessibility-report.json`
- Egress-denied evidence: `network-trace.json`

The repository stores the request hash and summary-only response record, not a
reconstructed full transcript. This is described as FAIR-oriented development
provenance, not FAIR certification.

## Open Verification

- Secure ingestion and malicious archive handling start in P003.
- Real `stylo` execution and computational parity remain P006.
- Complete browser workflows from upload to export remain P008, P009, and P012.
- Production security, isolation, load, and rollback remain P014.
- Barış Yücesan's structured expert walkthrough and final provenance/claim audit
  remain P015.
- The future `Launch Stylometry` entry on `lemmata.app` is deliberately deferred to
  a separate parent-site integration ticket.
