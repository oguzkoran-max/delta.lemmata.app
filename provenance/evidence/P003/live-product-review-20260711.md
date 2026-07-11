# P003 Live Product Review

## Scope

- Reviewed base commit: `daf3775c2a7a91273487f3e2368b6b0f051269ef`
- Additional surface: current secure-intake UI worktree
- Target: local Streamlit app at `http://127.0.0.1:8501`
- Review type: product, interaction, responsive, geometry, and console check
- Viewports: default desktop, 390 x 844, and 320 x 800

## Checks

1. The first screen remains the workbench rather than a landing page.
2. Corpus intake is visibly active while purpose is complete and later stages remain
   locked.
3. Individual TXT files and one ZIP archive are separate, explicit corpus roles.
   Choosing the ZIP role replaces the TXT uploader with a single ZIP uploader.
4. Metadata CSV has a separate uploader and is described as structural validation,
   not semantic metadata acceptance.
5. Upload, batch, archive-member, and expanded-content limits are visible beside
   the controls.
6. Continue and Run remain disabled with accurate reasons because corpus
   documentation, parameter validation, and the analysis engine are not connected.
7. At 390 px and 320 px, headings, segmented controls, uploader labels, uploader
   drop zones, limits, status, and experiment-map rows remain readable without
   incoherent overlap.
8. At 320 px, document scroll width, main scroll width, and client width are all
   exactly 320 px. No inspected button, segmented control, or upload drop zone has
   content overflow.
9. The browser log contains connection errors only from the intentional shutdown
   of the stale P002 development server at 08:09 UTC. The restarted P003 server
   produced no later warning or error during review.

## Automated Evidence Boundary

Streamlit AppTest separately covers empty, accepted TXT plus CSV, rejected invalid
UTF-8, and accepted ZIP states. This live browser surface did not transmit a local
corpus file. A tracked fresh-process Playwright audit will provide repeatable
screenshots, input interactions, request-host observation, and console evidence.

## Limits

This review is not a production deployment, packet capture, screen-reader
conformance session, real browser-chrome 200% zoom session, retention proof, or
scientific validation. Streamlit and proxy-level upload retention remain outside
P003 and must be evidenced in the lifecycle and deployment tickets.

## Verdict

No P0, P1, or P2 product finding. The secure-intake UI can proceed to the tracked
browser audit and independent adversarial review.
