# P014 Canlı Tasarım Denetimi ve Düzeltmeleri

Kapsam: `delta.lemmata.app` canlı public-alpha yüzeyinin uzman gözle
incelenmesi ve aile siteleriyle (`lemmata.app`, `lda.lemmata.app`) görsel
tutarlılık için iki tasarım düzeltmesi. A5.1 tasarım sistemi (Instrument Panel +
Quiet Ledger) sınırları içinde kalınmıştır; yeni özellik, runtime AI, login veya
analytics eklenmemiştir. Classic Delta / MFW / önişleme / yorum sınırları
değişmemiştir.

## Düzeltme 1 — Header build kimliği kısaltması

Sorun: Gerçek dağıtımda `DELTA_BUILD_ID` 40 karakterlik tam git SHA'sına
ayarlandığında header sağ üstteki meta satırı ("Version ... · Build <40 karakter>")
taşıyor ve `lemmata.app`'in temiz sürüm etiketine kıyasla dağınık görünüyordu.

Çözüm: Görünür build kimliği 12 karaktere kısaltıldı; tam SHA `title` özniteliğine
(hover ile açılan ipucu) taşındı. Provenans korunur, görsel yük azalır.
- Kod: `src/delta_lemmata/webapp.py` (`_render_header`)
- Test: `tests/test_phase_b_visual_contract.py::test_header_shows_a_short_build_and_keeps_the_full_sha_in_the_title`
- Kanıt: `screenshots/after-entry-sidebar-1440.png` (header "Build 25fc2cadbba2")

## Düzeltme 2 — Boş kenar çubuğu kolonu işlevsel özetle dolduruldu

Sorun: Review aşamasında sol kenar çubuğunda "Technical status" altında büyük bir
boş gri alan kalıyordu (bk. `screenshots/before-review-sidebar-1440.png`).

Çözüm: Boş alan, aşamaya duyarlı bir "Preparation summary" ile dolduruldu:
- Canlı hazırlık sayaçları: Independent works / Blockers / Warnings / Rights
  restrictions. Blocker ve warning sayısı sıfırdan büyükse ton renkleriyle
  (kırmızı / amber) işaretlenir, aksi halde nötr kalır.
- "Evidence reserved with every run" listesi: corpus health, parameter
  sensitivity, interpretive limits, run record. Corpus doğrulandığında corpus
  satırı "Validated for intake" durumuna geçer.

Sayaçlar `st.session_state` içindeki doğrulanmış `ValidationReport`'tan okunur;
corpus yoksa tümü sıfır ve nötr kalır. Daha önce ölü olan `evidence.*` UI
metinleri yeniden kullanıma alındı.
- Kod: `src/delta_lemmata/webapp.py` (`_sidebar_readiness_counts`,
  `_render_sidebar_summary`), `src/delta_lemmata/catalog.py`
  (`sidebar.summary_title`), `src/delta_lemmata/ui_theme.py`
  (`.delta-sidebar-summary`, `.delta-sidebar-metric*`, `.delta-sidebar-evidence*`)
- Testler:
  `tests/test_phase_b_visual_contract.py::test_sidebar_summary_flags_live_blockers_and_warnings`,
  `::test_sidebar_summary_stays_neutral_until_a_corpus_is_validated`,
  `tests/test_webapp_workflow.py::test_sidebar_readiness_counts_track_the_validated_report`,
  `::test_sidebar_readiness_counts_default_to_zero_without_a_report`
- Kanıt: `screenshots/before-review-sidebar-1440.png` (boş kolon),
  `screenshots/after-entry-sidebar-1440.png` (corpus yok, sayaçlar sıfır,
  "Awaiting corpus"), `screenshots/after-review-sidebar-1440.png` (works 3,
  warnings 12, rights 3, "Validated for intake").

## Düzeltme 3 — Deney haritası (stepper) aktif adım göstergesi

Sorun: Corpus aşamasında ilerleme haritasında aktif adımın (02 Corpus) teal üst
göstergesi, kutunun gri üst kenar çizgisinin ÜSTÜNDE havada duruyordu; ayrıca
Streamlit markdown listesinin `<li>` öğelerine uyguladığı stray `margin`
(0.2rem) aktif satırı kaydırıyordu. Etiketler (COMPLETE / UPLOAD / LOCKED)
çizgiye binmiş gibi görünüyordu (bk. `screenshots/before-stepper-1440.png`).

Neden: Aktif satırın `border-top: 3px` göstergesi kutu kenarıyla çakışıyordu ve
`.delta-map` kırpma (`overflow: hidden`) uygulamadığı için köşelerden taşıyordu.
Streamlit'in `[data-testid] li` kuralı tek-class `.delta-map-row` margin
sıfırlamasını specificity'de yeniyordu.

Çözüm (A5.1 içinde):
- `.delta-map` artık `overflow: hidden` ile göstergeyi yuvarlak çerçeveye kırpar.
- Aktif adım göstergesi `border-top` yerine `box-shadow: inset 0 3px 0 0 teal`
  oldu; layout'u kaydırmaz, çerçeve içinde flush durur.
- Aktif hücreye `--delta-mint` wash verildi; teal aksan artık stray line değil,
  ailenin mint=aktif diliyle tutarlı net bir "aktif sekme" olarak okunur.
- Streamlit `<li>` margin'i daha spesifik `.delta-map-list .delta-map-row`
  selector'uyla sıfırlandı; tüm hücreler çerçeveye hizalandı.
- Kod: `src/delta_lemmata/ui_theme.py` (`.delta-map`, `.delta-map-list
  .delta-map-row`, `.delta-map-row.is-active`)
- Test: `tests/test_phase_b_visual_contract.py::test_experiment_map_active_step_reads_as_a_clean_tab`
- Kanıt: `screenshots/before-stepper-1440.png`, `screenshots/after-stepper-1440.png`,
  `screenshots/stepper-before-after-1440.png` (önce/sonra, 1440 desktop).

## Doğrulama

`bash scripts/verify.sh` yeşil: ruff format/check, mypy, şema doğrulayıcılar,
`pytest --cov` %100 satır + dal kapsamı, metadata/records/repo-scan, R-lock.

Görüntüler `MANIFEST.sha256` ile sabitlenmiştir. Canlı sunucuya dağıtım
yapılmamıştır; değişiklikler PR #15 (draft) üzerinde tutulmaktadır.
