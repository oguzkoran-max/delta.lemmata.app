# P004 Automated Acceptance Rehearsal Checkpoint

**Tarih:** 2026-07-12

## Kullanici Karari

- Oğuz ara testleri Codex'in yürütmesini istedi.
- Birlikte yapılacak insan walkthrough'u ürün gerçekten hazır olduğunda yapılacak.
- Bu karar insan kabulünü yok etmez; onu son ürün kapısına erteler.
- Safari, VoiceOver, bilimsel geçerlilik veya genel kullanılabilirlik otomatik
  Chromium testinden türetilmeyecek.

## Uygulama

- P004 browser harness'a fail-closed rights correction turu eklendi.
- `permission_required` önce blocker üretir ve confirmation'ı kapatır.
- Exact correction `rights_status` alanına döner ve guided değerleri korur.
- `analysis_only` sonrasında upload/analysis permitted, export/public
  redistribution prohibited olur.
- Confirmation yalnız blocker kalmadığında inventory hash'ine bağlanır.
- Selectbox, render-count, checkbox ve download sıralaması Streamlit yeniden çizim
  davranışına karşı kararlı hale getirildi.

## Kanit

- Brief: `prompts/P004-automated-acceptance-rehearsal.md`
- Validation: `provenance/evidence/P004/automated-acceptance-rehearsal-validation.md`
- Passing browser evidence:
  `provenance/evidence/P004/automated-acceptance-rehearsal-attempt-12/`
- Working-tree full gate: 468 test, 3.174 statement, 880 branch, yüzde 100 coverage.
- Final browser: six viewport + Guided TXT + rights correction + ZIP, no egress,
  no console error, no payload echo.

## Siradaki Kapi

Implementation commit'i fresh no-hardlinks clone'da yeniden kur, full gate ve
browser audit'i tekrarla, GitHub CI'yi doğrula. Ancak bundan sonra P004 teknik
kapanışı ve P005 geçişi değerlendirilebilir.
