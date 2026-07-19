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

## Düzeltme 4 — Sidebar evidence satırları uniform stacked ledger

Sorun: Düzeltme 2'nin evidence listesinde yalnız "Parameter sensitivity /
Awaiting configuration" satırı, ikisi de uzun olduğu için ~200px kolonda çift
satıra kırılıyor, diğer üç satır tek satır kalıyordu; ledger dengesiz
görünüyordu (DOM ölçümü: bu satır 42px, diğerleri 21px).

Çözüm: `.delta-sidebar-evidence-row` yan-yana (`space-between`) yerine dikey
stack (`flex-direction: column`) oldu; her madde adı üstte (ink), durumu altta
(muted, sola hizalı). Tüm satırlar uniform iki satır, tutarlı ritim. Satırlar
arası boşluk 0.5rem'e çıkarıldı ki çiftler ayrışsın. Etiket/durum metinleri
kısaltılmadı (anlam korundu).
- Kod: `src/delta_lemmata/ui_theme.py` (`.delta-sidebar-evidence`,
  `.delta-sidebar-evidence-row`)
- Kanıt: `screenshots/sidebar-evidence-before-after-1440.png`

Not: Aynı turda mobil (purpose→corpus boşluğu, upload kartı iç padding) ve mobil
header kenar boşluğu adayları DOM ile ölçüldü ve gerçek sorun olmadığı görüldü
(kart padding-top yalnız 14px; header sağ boşluk 14px standart); değişiklik
yapılmadı.

## Düzeltme 5 — Tipografi hizası (LDA karşılaştırmalı) + tekrar metin temizliği

Soru: "Yazı boyutu lda.lemmata.app ile benzer mi? Metinler kullanıcıyı yoruyor
mu?" Cevap ölçümle verildi (Playwright computed-style, canlı LDA + canlı
lemmata.app + lokal Delta):

| Ölçüm | Delta (önce) | LDA canlı | lemmata.app |
|---|---|---|---|
| Gövde metni | 16px / lh 1.6 Source Sans | 16px / lh 1.6 Source Sans | 16px Inter |
| En küçük yazı | 11.52px (mikro-etiket) | 13.6px | 9.6px |
| Giriş ekranı kelime | 569 | 190 | 388 |

Bulgular ve düzeltmeler:
1. Gövde tipografisi LDA ile ZATEN birebir aynı (16px Source Sans); başlık
   hiyerarşisi bilinçli olarak lemmata.app'e (Inter hero) yakın. Değişiklik yok.
2. Mikro-etiket katmanı (kicker, eyebrow, stepper durumu, alan etiketleri,
   evidence başlığı: 0.72/0.74rem = 11.5-11.8px) LDA'nın en küçük yazısından
   belirgin küçüktü ve 12px okunabilirlik tabanının altındaydı. Tüm
   0.72/0.74rem değerleri 0.75rem'e (12px) çekildi; skala sadeleşti (sistemde
   zaten 12px kademesi vardı). Sonrası ölçüm: en küçük yazı 12.0px.
3. Metin yükü: giriş ekranı 569 kelime taşıyordu (LDA'nın ~3 katı). Kök neden
   sayfa genelinde aynı mesajın ÜÇ kez tekrarıydı: "Delta metinleri
   parametrelerden önce belgeler" hem hero 3. satırında, hem sidebar
   girişinde, hem "Why parameters come later" bloğundaydı. Hero'daki mükerrer
   cümle kaldırıldı; bilimsel çapa cümlesi ("Every comparison is relative to
   your corpus.") korundu. Katalog envanteri (634 key, 5093 kelime) cümle
   düzeyinde başka gerçek tekrar göstermedi (yalnız 2 kasıtlı bağlam çifti);
   uzun metinler bilinçli bilimsel açıklayıcılar olduğundan kısaltılmadı
   (yorum-sınırları dili audit kısıtı gereği dokunulmaz).
- Kod: `src/delta_lemmata/ui_theme.py` (0.72/0.74→0.75rem, 11 kural),
  `src/delta_lemmata/catalog.py` (`setup.corpus_scope`)
- Kanıt: `screenshots/after-entry-typography-1440.png` (sonrası; min font 12px,
  561 kelime)

(Önceki turda "açık bulgu" olarak bırakılan mobil rehber sırası, sonraki turda
Düzeltme 8 kapsamında kapatıldı; aşağıya bakınız.)

## Düzeltme 6 — Sidebar sayaç tonlarında WCAG kontrastı + palet disiplini

Öz-denetim bulgusu: Düzeltme 2'de eklenen sidebar sayaçlarının warning tonu
`--delta-amber` (#b8860b) idi; beyaz zeminde 3.25:1 kontrast, WCAG AA normal
metin eşiğinin (4.5:1) altında. Blocker tonu ise palet dışı hardcoded #b42318
kullanıyordu. İkisi de sistemin metin-katmanı token'larına çekildi:
`--delta-coral-text` (blocker) ve `--delta-amber-text` (7.82:1, warning) —
review metriklerinin kullandığı token'larla aynı.
- Kod: `src/delta_lemmata/ui_theme.py` (`.delta-sidebar-metric-blocker`,
  `.delta-sidebar-metric-warning`)

## Düzeltme 7 — MDS bindirme bugı: gizli kalan unknown-holdout noktası

Sonuç ekranı denetimi (sentetik `ResultViewV1` ile lokal render, R worker
gerekmeden): kare MDS grafiği CSS'i (`aspect-ratio: 60/61`,
owner-onaylı A5.1) grafiği geniş yerleşimde ~691px'e büyütürken Streamlit'in
yerleşim konteyneri `height=360` parametresinden 360px ayırıyordu. Grafik 331px
taşıyor, koordinat tablosu grafiğin üstüne biniyor ve alt bölgedeki noktalar
tablonun ARKASINDA kalıyordu. Sentetik senaryoda gizlenen nokta tam da
**unknown holdout** (D04) idi; bilimsel görüntüde veri noktası saklanması bu
turun en kritik bulgusudur. DOM ölçümü: grafik 691px, konteyner 360px,
tablo-üstü < grafik-altı (bindirme); düzeltme sonrası konteyner 691px,
bindirme yok, D04 elması görünür.

Durum: BULGU DOĞRULANDI, DÜZELTME ERTELENDİ (owner kararı gerekli).
Denenen çözüm (konteynere `height: auto`) bindirmeyi giderdi ve D04'ü görünür
yaptı (bk. after görseli), ancak CI'ın P009 sonuç-viewport kapısındaki
`mds_metric_aspect_pass` sözleşmesini (iç çizim çerçevesi ±2px kare; Vega
autosize mark sınırlarını da sayar) 1280 bandında bozdu — kare sözleşmesi,
360px Streamlit slotu ve `60/61` / `60/61.3` aspect sabitleri birlikte
kalibre edilmiş bir sistem. Tek parça CSS fix'i bu sistemi viewport'a bağlı
biçimde oynatıyor; kalıcı çözüm slot yüksekliği + aspect sabitleri + kare
sözleşmesinin birlikte yeniden kalibrasyonunu istiyor. Deneme geri alındı.
- Kanıt: `screenshots/before-mds-overlap-1440.png` (tablo grafiğe binmiş,
  D04 görünmez; kusur bugün de canlı kodda), `screenshots/after-mds-square-1440.png`
  (denenen fix'in D04'ü nasıl görünür kıldığı; referans)

## Düzeltme 8 — Grafik etiketlerinde sigla→başlık tutarlılığı

Sonuç yüzeyleri iki dil konuşuyordu: matris tablosu + heatmap eksenleri +
MDS nokta etiketleri sigla (D01..) kullanırken komşu ve koordinat tabloları
başlık ("Early novel") kullanıyordu; ekranda görünür bir D01→başlık eşlemesi
yoktu (yalnız hover tooltip). Gerçek 15+ metinlik korpusta matris/heatmap
çözülemez olurdu.

Çözüm (pinli sözleşmelere dokunmadan): heatmap eksen etiketleri
"D01 · Kısaltılmış Başlık" biçimine geçirildi (`_chart_axis_label`, 14
karakter kısaltma); sigla↔başlık eşlemesi artık heatmap'te görünür ve matris
tablosuyla çapraz-referans kurulabiliyor. MDS nokta etiketleri de aynı biçime
alınmıştı ancak GERİ ALINDI: uzun nokta etiketleri Vega autosize'ında mark
sınırlarına dahil olup iç çerçeveyi daraltıyor ve `mds_metric_aspect_pass`
kare sözleşmesini (±2px) bozuyor — etiket geometrisi o kalibrasyonun parçası.
MDS noktaları sigla + hover-tooltip başlık olarak kaldı (eşleme hemen üstteki
heatmap'te görünür). Semantic tablolar ve canonical export DEĞİŞMEDİ.
- Kod: `src/delta_lemmata/webapp.py` (`_chart_axis_label`, `_render_heatmap`
  iki katman, `_render_mds` veri + metin katmanı)
- Testler: `tests/test_webapp_workflow.py`
  (`test_chart_axis_label_pairs_key_with_a_truncated_clean_title`,
  güncellenen `test_result_charts_bypass_pandas_string_inference`)
- Kanıt: `screenshots/after-heatmap-labels-1440.png`,
  `screenshots/after-mds-square-1440.png`

Ek temizlik: `deploy/public-alpha/README.md` içindeki sabit sunucu IP'si üç
yerde `DELTA_HOST` ortam değişkenine çekildi (repo public olduktan sonra
gereksiz literal ifşayı kaldırır; prob semantiği değişmez).

Mobil purpose-rehberi sırası önce seçimin ardına taşındı, sonra GERİ ALINDI:
CI'daki P009 entry-viewport kapısı (`purpose_guide_layout_pass`) mobilde
rehberin upload bölümünün ALTINDA olmasını açıkça şart koşuyor — yani mevcut
yerleşim tesadüf değil, denetlenmiş bilinçli bir karar (mobilde aksiyon-önce
ilkesi; rehber katlanır `<details>` olarak altta). Önceki turun "açık bulgu"su
böylece "kusur değil, sözleşmeli tasarım kararı" olarak kapandı. Sözleşmeyi
kendi tercihimle değiştirmek yerine yerleşim korundu; farklı bir mobil bilgi
sırası istenirse bu owner kararıyla gate ile birlikte değişmeli.

## Doğrulama

`bash scripts/verify.sh` yeşil: ruff format/check, mypy, şema doğrulayıcılar,
`pytest --cov` %100 satır + dal kapsamı, metadata/records/repo-scan, R-lock.

Görüntüler `MANIFEST.sha256` ile sabitlenmiştir. Canlı sunucuya dağıtım
yapılmamıştır; değişiklikler PR #15 (draft) üzerinde tutulmaktadır.
