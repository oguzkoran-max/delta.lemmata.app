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
- Exact implementation commit: `9f3124a65216fd1c0f6d459cfe6a3049f51baa07`.
- Exact clean-clone run: `RUN-20260712-0005`, 468 test, 3.174 statement, 880
  branch, yüzde 100 coverage ve expanded browser audit; clone temiz kaldı.

## Siradaki Kapi

Exact-commit kanıtını provenance-link commit'inde mühürle ve GitHub CI'yi doğrula.
CI yeşil olursa `HD-20260712-0002` sınırlarıyla P004 teknik kapanışını kaydet;
ortak final owner walkthrough'u P015 ürün-hazır kapısında açık tut.
