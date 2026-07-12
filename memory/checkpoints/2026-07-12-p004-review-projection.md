# P004 Review Projection Checkpoint

**Tarih:** 2026-07-12

## Uygulanan

- Canonical inventory ve hash-matching ValidationReport için payload-free immutable
  Review projection eklendi.
- Genre, audience, adaptation, collection ve acquisition source type composition
  boyutlarının her biri bütün work kayıtlarını paydada tutuyor.
- Unknown, not-applicable, missing source ve conflicting source kategorileri görünür.
- Identity, chronology, edition, source, classification, rights ve normalization
  için work x 7 Metadata Completeness Matrix üretildi.
- Complete rights documentation ile action permission birbirinden ayrıldı; score yok.
- Decorative bars, semantic tables ve iki CSV aynı projection key'lerini kullanıyor.
- Review CSV'leri indirilmeden önce değişmeyen P003 CSV politikasından geçiriliyor.
- Table scroll bölgelerine accessible name, keyboard focus ve visible outline eklendi.
- Review download sayısı canonical inventory, validation, metadata, composition ve
  completeness olmak üzere beşe çıktı.

## Kanıt

- 37 projection testi: 415 statement ve 178 branch'in yüzde 100'ü.
- Tam aday: 457 test, 2.984 statement ve 830 branch'in yüzde 100'ü.
- Fresh-process Playwright: visual/table/CSV key parity, work x 7 matrix, üç
  focusable region, beş download ve altı Review viewport geçti.
- İlk focus failure ve manuel incelemede reddedilen clipped-count screenshot korundu.
- Kanıt: `provenance/evidence/P004/review-projection-validation.md`.

## Açık Sınır

P004 kabul edilmedi. Matrix field path'leri henüz exact editable field link'i değil.
Selectable horizontal timeline, explicit mapping/rights confirmation, guided ZIP
member catalog, human Safari/VoiceOver walkthrough, exact-commit/CI ve clean-clone
kapanışı bekliyor. Scientific analysis, runtime AI ve deployment yok.

## Sıradaki Tek İş

Selectable horizontal timeline ile explicit final mapping/rights confirmation
kapısını tasarlamak; aynı dilimde matrix correction targets için truthful routing
kurmak.
