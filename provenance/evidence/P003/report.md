# P003 Secure Ingestion Report

## Result

P003 implements a fail-closed application boundary for explicitly declared corpus
TXT, corpus ZIP, and metadata CSV inputs. It validates browser uploads without
creating analysis state or invoking `stylo`. The interface remains English-only;
corpus documentation, metadata semantics, parameters, analysis, export, and
production lifecycle controls remain locked.

## Role And Type Policy

1. The user chooses individual TXT files or one ZIP archive before bytes are
   inspected. Metadata CSV uses a separate uploader.
2. The selected role determines the required extension and parser.
3. Client-declared MIME is untrusted advisory metadata. When present it must match
   the selected role; absence does not replace content validation and is not itself
   treated as proof of type.
4. TXT and CSV require strict UTF-8, Unicode NFC, bounded text structure, and
   role-specific parsing. Known binary/document signatures and ZIP masquerades are
   rejected as type mismatches.
5. Metadata acceptance in P003 is structural only. Column meaning, corpus matching,
   chronology, grouping, provenance, and rights belong to P004.

## ZIP V1 Subset

P003 accepts only a deliberately narrow ZIP subset:

- exact start and end of container, zero comment, one disk, and no ZIP64;
- raw EOCD, central-directory, and local-header consistency before `ZipFile`,
  including version-needed, flags, method, DOS time/date, CRC, sizes, and name;
- no encryption, data descriptors, extra fields, member comments, gaps, overlaps,
  unsupported flags, or unsupported compression methods;
- only stored or deflated TXT members and consistent empty directory inventory;
- no nested archive, link, device, ambiguous path, reserved name, absolute path,
  traversal, normalization collision, case-fold collision, or file/directory prefix
  collision;
- complete bounded preflight and one text scan before workspace creation, including
  remaining batch expansion budget before member decompression, followed by
  server-generated flat names, exclusive no-follow writes, and one second-read
  SHA-256 verification.

The strict subset intentionally rejects some valid but more complex ZIP files. The
product must explain that users can recreate those archives as simple standard ZIP
files; P003 does not silently broaden the parser.

## Versioned Limits

The packaged `ingestion-limits-v1` profile is the single policy source.

| Limit | Value |
|---|---:|
| Per upload | 25 MiB |
| Batch bytes | 50 MiB |
| Batch expanded bytes | 100 MiB |
| Batch files | 50 |
| Text characters | 20,000,000 |
| Lines | 500,000 |
| Tokens | 3,000,000 |
| Characters per token | 4,096 |
| ZIP members | 200 |
| Central directory | 1 MiB |
| Expanded ZIP | 50 MiB |
| Member bytes | 10 MiB |
| Compression ratio | 100:1 |
| Path depth | 3 |
| Path bytes | 240 |
| CSV rows | 20,000 |
| CSV columns | 64 |
| CSV cell characters | 16,384 |

The profile is tracked, included in the wheel, immutable at runtime, locked field by
field in regression tests, and cannot be overridden by an upload, browser session,
or environment variable.

## Payload And Error Handling

- User labels are validated display labels and never storage paths.
- Receipts contain generated IDs, controlled labels, counts, SHA-256, and the limit
  profile identifier, not text or CSV cells.
- Rejections expose only stable content-free error codes and explanatory category
  copy. Public rejection objects detach Python exception cause and context chains,
  including decoder, archive, and operating-system exceptions.
- A rejected Streamlit submission rotates all uploader keys through a rerun. The
  rerun retains only one stable error code, clears rejected filenames and bytes from
  the rendered widget state, and creates no analysis state.
- Extraction failures remove Delta-created workspaces. If cleanup itself fails, the
  result is a stable cleanup error rather than a success.

## Verification

The evidence package includes:

- fixed TXT, CSV, ZIP, cleanup, and disk-canary fixtures;
- three deterministic seeds and 128 cases per malicious family;
- 1,536 generated malicious cases and 1,152 generated positive controls;
- statement and branch coverage fixed at 100%;
- six-viewport fresh-process browser audit with synthetic TXT, CSV, rejected UTF-8,
  and ZIP interactions;
- full-body payload and rejected-filename absence checks, uploader reset checks,
  semantic upload regions, an explicitly named progressbar, observed browser-host
  recording, and console capture;
- retained failed attempts and additive path errata.

The final test count, exact commit, Run IDs, clean-clone replay, and evidence manifest
will be added after the implementation commit; none is claimed by this pre-closure
report.

## Boundaries

P003 does not establish:

- metadata meaning, rights, source provenance, or corpus readiness (P004);
- successful-upload retention, timeout/cancel/crash/restart cleanup, janitor behavior,
  or cross-session isolation (P005);
- R execution or scientific validity (P006 onward);
- export escaping and downloadable package safety (P009/P012);
- reverse-proxy, container, host, swap, backup, snapshot, or production log retention
  (P014);
- CE-14's production deletion times or any FAIR-compliant/certified claim.

All browser inputs used for P003 evidence are synthetic. No Pinocchio or other
research corpus was uploaded.
