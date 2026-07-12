# P004 Guided ZIP Member Catalog Checkpoint

**Tarih:** 2026-07-12

## Uygulanan

- P003'ün zaten hesapladığı safe member label, SHA-256, byte, line, token ve limit
  profile değerleri immutable, payload-free `ArchiveMemberReceipt` olarak açıldı.
- Parser, limitler ve rejection davranışı değiştirilmedi; ZIP yeniden parse veya
  extract edilmedi.
- Individual TXT ve ZIP member'lar aynı deterministic `ValidatedCorpusUnit`
  catalog'una projekte ediliyor.
- Upload ekranı member catalog'u gösteriyor; Continue sonrası yalnız P004 catalog
  kalıyor, browser payload ve storage adları state'e taşınmıyor.
- İki member iki guided form ve iki Review work satırı üretiyor.
- Nested safe member path versioned metadata CSV template politikasından geçiyor.

## Kanıt

- Focused suite: 125 test.
- Final gate: 467 test, 3.165 statement, 878 branch, yüzde 100 coverage.
- Fresh-process Playwright: individual-TXT regression + two-member ZIP catalog,
  two forms, two-work Review, visible unknown-rights blocker, mobile no-overflow,
  no payload echo, no egress ve clean console geçti.
- Dört başarısız harness/oracle koşusu ayrı tutuldu.
- Ayrıntı:
  `provenance/evidence/P004/guided-zip-member-catalog-validation.md`.

## Açık Sınır

P004 insan tarafından kabul edilmedi. Exact-commit clean clone, GitHub CI ve Oğuz'un
terminology/negative-rights/correction/timeline/confirmation/ZIP Safari-VoiceOver
walkthrough'u bekliyor. Scientific analysis, runtime AI ve deployment yok.

## Sıradaki Tek İş

Birleşik P004 adayını exact commit üzerinde clean clone ve GitHub CI ile doğrula;
sonra Oğuz'un insan kabul turunu yürüt.
