# P017 Deployment Record — Living Corpus narrative replaces P016 files

Date: 2026-07-22 · Executed by: Claude Code · Owner authorization: Oğuz Koran,
same-day chat ("bunu deploy ettikten yani canlıya aldıktan sonra şimdi sırada
ne var?" — deployment presupposed after the final expert review and two
owner-reported defects were fixed and regression-tested).

## What changed in production
- File swap only: `/opt/delta-narrative/how-delta-works/` now carries the P017
  page (index.html + assets: styles.css, narrative.js, 3 self-hosted woff2
  fonts + OFL licence + FONTS.md, keyvis-hero.jpg/-02/-03/-04.jpg,
  keyvis-hero.mp4). Caddy route from P016 reused unchanged; no Caddyfile, DNS,
  nginx, container or systemd change; workbench untouched.
- Backup of the previous (P016) files:
  `/root/how-delta-works.pre-p017-202607221510` on the VPS.
- Aggregate SHA-256 over every deployed file verified identical local↔remote:
  `25e4503c833832df880af0b2fbbe6f127a0afc7400f7d5f6672f3086fda016be`.

## Post-deploy verification (all measured 2026-07-22)
- `GET /how-delta-works/` → 200, title "How Delta works — The Living Corpus".
- `GET /how-delta-works` → 308; styles.css/keyvis-hero.jpg/Fraunces woff2 → 200.
- `keyvis-hero.mp4` with Range → 206 (streaming ok).
- Workbench `/_stcore/health` → 200; `lda.lemmata.app/_stcore/health` → 200.
- HSTS / nosniff / DENY headers present.
- Visual check over HTTPS: video hero playing, headline, CTA, status, scroll cue.

## Rollback
`rm -rf /opt/delta-narrative/how-delta-works && cp -a /root/how-delta-works.pre-p017-202607221510 /opt/delta-narrative/how-delta-works`
(no service reload needed; static files only).

## Deployment status
DEPLOYED AND VERIFIED — https://delta.lemmata.app/how-delta-works/
