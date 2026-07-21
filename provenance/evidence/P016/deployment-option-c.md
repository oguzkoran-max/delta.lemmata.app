# P016 Deployment Record — Option C (narrative at /how-delta-works/)

Date: 2026-07-20 · Executed by: Claude Code · Owner authorization: Oğuz Koran,
same-day chat instruction ("tüm süreci sen üstlen... devreye alalım siteyi"),
following the recommended Option C in `adr-proposal-routing.md`.

## What changed in production
- Static files copied to `/opt/delta-narrative/how-delta-works/` on the VPS;
  SHA-256 of all three files verified identical to repo (`index.html` 18,532 B,
  `assets/styles.css` 18,772 B, `assets/narrative.js` 4,557 B; total 41,861 B).
- `/etc/caddy/Caddyfile` delta.lemmata.app block: added
  `redir /how-delta-works /how-delta-works/ 308` and a
  `handle_path /how-delta-works/*` static file_server (root above, gzip);
  the existing workbench `reverse_proxy` wrapped unchanged in `handle {}`.
  Backup retained at `/root/Caddyfile.pre-p016-narrative`.
- Nothing else touched: no DNS, no nginx, no container, no systemd, no
  workbench release change. Narrative traffic is served by Caddy directly and
  never crosses the capacity-tight nginx gateway (which is why the ADR's
  gateway-capacity precondition does not gate this surface; it remains an open
  recommendation for workbench traffic itself).

## Post-deploy verification (all measured)
- `GET /how-delta-works/` → 200, correct title/H1/badges content.
- `GET /how-delta-works` → 308 to the slashed URL.
- `GET /how-delta-works/assets/styles.css` → 200.
- Workbench `/_stcore/health` → ok; `lda.lemmata.app/_stcore/health` → ok.
- Security headers on the narrative (inherited from the site block): HSTS,
  nosniff, DENY, no Server banner.
- Visual check over HTTPS in a browser: hero, badges, progress hairline,
  reveals, CTA to the workbench root.

## Rollback
`cp -a /root/Caddyfile.pre-p016-narrative /etc/caddy/Caddyfile && systemctl
reload caddy` (removes the route; static directory may stay or be deleted).
Repo state is unaffected by rollback.

## Deployment status
DEPLOYED AND VERIFIED — URL: https://delta.lemmata.app/how-delta-works/
(workbench remains at the root; P002/P004 direct-workbench contract intact).
