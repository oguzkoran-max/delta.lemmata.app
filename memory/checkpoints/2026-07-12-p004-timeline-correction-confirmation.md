# P004 Timeline, Correction, and Confirmation Checkpoint

**Tarih:** 2026-07-12

## Uygulanan

- Work timeline canonical hash-bound projection'a eklendi; known dates first,
  unknown dates last ve seçim ayrıntısı semantic table ile aynı row key'i taşıyor.
- Metadata Completeness Matrix'teki her non-complete field path, exact work ve
  section correction target'ına bağlandı.
- Guided dönüşte metadata kaybını önlemek için payload-free input state'i korundu.
- CSV-origin inventory için tutulmayan CSV'yi taklit eden boş form açılmıyor; exact
  `work_id` ve source CSV field düzeltmesi isteniyor.
- Mapping ve rights acknowledgement canonical inventory SHA-256'ya bağlandı;
  blocker varsa disabled, rebuild olursa invalidated.
- Mobilde Streamlit header'ın custom wordmark'ı örtmesi düzeltildi.

## Kanıt

- Focused suite: 84 test.
- Final gate: 464 test, 3.132 statement, 868 branch, yüzde 100 coverage.
- Fresh-process Playwright: timeline/table parity, keyboard confirmation, dört
  focusable data region, beş download, altı viewport, no overflow, no egress,
  no payload echo ve unoccluded brand geçti.
- Interaction failure, pre-header-fix passing run ve final passing run ayrı tutuldu.
- Ayrıntı:
  `provenance/evidence/P004/timeline-correction-confirmation-validation.md`.

## Açık Sınır

P004 kabul edilmedi. Guided ZIP member catalog, Oğuz'un Safari/VoiceOver ve
terminology/negative-rights walkthrough'u, exact-commit clean clone ve GitHub CI
bekliyor. Scientific analysis, runtime AI ve deployment yok.

## Sıradaki Tek İş

Guided ZIP için güvenli member-level payload-free catalog tasarla; ardından birleşik
P004 UI adayını exact commit/CI ve insan kabul turuna hazırla.
