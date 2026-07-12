# P004 Guided Corpus Flow Checkpoint

**Tarih:** 2026-07-12

## Uygulanan

- Individual TXT için Upload -> Describe -> Review akışı domain modeline bağlandı.
- Upload sonrasında ham metin ve transient storage kimliği session state'ten çıkarılıyor.
- Guided editor work, author, chronology, edition, source, confound ve rights alanlarını
  immutable P004 inventory'ye dönüştürüyor.
- Unknown rights fail-closed kalıyor; Rights Action Matrix dört eylemi ayrı gösteriyor.
- Style Over Time için mixed author set ve mixed language yeni blocker oldu.
- Canonical inventory JSON, validation report JSON ve metadata CSV indirilebiliyor.
- Tek stepper, mobile compact layout ve action-first upload sırası uygulandı.

## Kanıt

- `./scripts/verify.sh`: 418 test, yüzde 100 statement/branch coverage, tüm kapılar yeşil.
- Fresh-process Playwright: altı viewport ve guided E2E geçti.
- Kanıt: `provenance/evidence/P004/guided-corpus-workflow-validation.md`.

## Açık Sınır

P004 kabul edilmedi. Composition bars, Metadata Completeness Matrix, selectable
horizontal timeline, explicit final confirmation, ZIP member catalog, human
Safari/VoiceOver walkthrough, exact-commit/CI ve clean-clone kapanışı bekliyor.

## Sıradaki Tek İş

Validated inventory'den composition bars ve Metadata Completeness Matrix üretmek;
her görseli aynı nesneden türetilen text/table ve downloadable CSV ile bağlamak.
