# P004 Beginner-First Entry Experience Checkpoint

**Tarih:** 2026-07-12

## Uygulanan

- Teknik-first giriş, stilometriyi basit ve yöntemsel olarak doğru tanımlayan tek
  semantic giriş yüzeyine dönüştürüldü.
- Observe -> Compare -> Interpret kavramsal haritası eklendi ve bunun analiz sonucu
  olmadığı açıkça yazıldı.
- Amaçlar Compare Texts, Compare Groups ve Trace Style Over Time olarak sadeleştirildi.
- Her amaç için Question, Why use it ve Do not conclude alanları sürekli görünür.
- Giriş ile gerçek Upload akışı aynı sayfada kaldı; splash, modal veya sahte sonuç
  grafiği eklenmedi.
- Masaüstü, mobil ve 320px reflow düzenleri ayrı kurallarla düzeltildi.

## Kanıt

- Profesyonel brief: `prompts/P004-entry-experience-redesign.md`
- Doğrulama raporu:
  `provenance/evidence/P004/entry-experience-redesign-validation.md`
- Final browser sonucu:
  `provenance/evidence/P004/browser-audit-entry-redesign-passed-2026-07-12/browser-audit.json`
- Focused AppTest: 15 test geçti.
- Fresh-process Playwright: altı viewport, individual TXT ve two-member ZIP geçti.
- `./scripts/verify.sh`: 467 test, 3.167 statement, 880 branch ve yüzde 100
  coverage; typing, metadata, 57 kayıt, repository scan ve R lock geçti.

## Saklanan Başarısızlıklar

Yanlış Python ortamı, üç stale-widget testi, iki in-app screenshot timeout'u, ilk
viewport eşiği, eski copy oracle'ı, 320px first-action ve 30px H1 expectation
başarısızlıkları silinmedi. Beş budget-exhausted ajan denemesi bağımsız onay olarak
sayılmadı.

## Açık Sınır

Scientific analysis, AI, storage, deployment ve parent-site launch eklenmedi. P004
insan kabulü verilmedi. Full repository gate, exact commit, CI ve revize
Safari/keyboard/VoiceOver walkthrough ayrı kapılardır.

## Sıradaki Tek İş

Tasarım commit'ini exact clone'da yeniden üret, CI sonucunu bağla ve ardından
Oğuz'un adım adım insan kabul turunu başlat.
