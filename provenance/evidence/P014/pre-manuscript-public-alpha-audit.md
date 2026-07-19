# P014 Canlı Public-Alpha Kapsamlı Denetim ve Düzeltme

**Tarih:** 2026-07-18
**Denetleyen:** Claude Code (Opus 4.8), yedi bağımsız mercek + adversaryel sentez
**Amaç:** Makale yazımına başlamadan önce canlı `delta.lemmata.app` public-alpha sürümünün genel denetimi, doğrulanan sorunların düzeltilmesi ve makale için kalan bilimsel kanıt açıklarının belirlenmesi. Bu belge makalenin gönderime hazır olduğunu iddia etmez.

## 1. Kapsam ve ortam

- **Başlangıç SHA:** `3cfe0713a7159fcbedb0c390e801698dd09ae77d` (origin/main)
- **Denetim dalı:** `claude/p014-pre-manuscript-audit` (origin/main'den açıldı)
- **Uygulama (kod düzeltmeleri) final SHA:** `22e3e1d4b3db8fb6fdade7a90be68ca20d085825` (son kod commit'i; Caddy savunma-derinliği, neden-özel + hata-sınıfına duyarlı intake yönlendirmesi, metrik wrap). Kod fix commit zinciri: `0980833` → `02527cc` → `ce89a5a` → (R1) XFF-reclassify → `22e3e1d`.
- **Kanıt/rapor SHA:** bu belgeyi ve güncel görselleri ekleyen doc commit'i (bu commit uygulama SHA'sından SONRA gelir; PR #15'in nihai head'i). Uygulama SHA'sı ile kanıt SHA'sı bilinçli olarak ayrıdır: kod fix'leri ölçülebilir CI kapısından geçer, rapor/kanıt onun üstüne yazılır.
- **Canlı Delta:** `https://delta.lemmata.app` — home HTTP 200, `/_stcore/health` = `ok`
- **Aynı VPS'teki LDA:** `https://lda.lemmata.app` — home 200, health `ok` (yalnız read-only gözlem; değişmedi)
- **Yerel doğrulama:** `./scripts/verify.sh` düzeltmeler öncesi ve sonrası geçti; taze klon kaynak testi yapıldı
- **Test corpus'u:** yalnız depo içi sentetik fixture; kullanıcıya ait gerçek metin kullanılmadı

Çalışma ağacı denetim başında temizdi (kullanıcı değişikliği yoktu). Hiçbir canlı sunucu, Caddy, DNS, Docker registry veya LDA dosyasına dokunulmadı.

## 2. Yönetici kararı

**CONDITIONAL GO** — makale *tasarımına* başlanabilir. P0/P1 blocker yok.

Uygulama yüzeyi bilimsel olarak dürüst ve tutarlı; canlı altyapı sağlıklı ve güvenli başlıklarla korunuyor. Bu turdaki iki masaüstü/UX P2 kusuru düzeltildi ve testlendi; SEC-XFF kalemi bağımsız Codex incelemesi sonrası P1'den savunma-derinliğine indirildi (aşağıya bakınız) ve yine de uygulandı. Kalan açıkların tamamı P011/P012/P013/P015 için zaten *üretilecek* kanıt kalemleridir. Bu karar yalnız "makale tasarımına başlayabilir miyiz?" sorusuna cevap verir; P011-P015 kapılarının tamamlandığını veya sürümün gönderime hazır olduğunu söylemez.

## 3. Bulunan sorun sayıları

| Ağırlık | Adet | Bu turda düzeltilen | Ertelenen |
|---|---|---|---|
| P0 (kullanılamaz/yanıltıcı) | 0 | 0 | 0 |
| P1 (ana akış/güvenlik/ciddi erişilebilirlik) | 0 | 0 | 0 |
| P2 (profesyonel kalite kaybı, yayın-engeli değil) | 3 | **2** | 1 (makale-açığı) |
| P3 (küçük cila / gelecek) | 7 | 0 | 7 |
| Savunma-derinliği (kusur değil, uygulandı) | 1 | 1 (SEC-XFF) | 0 |

Üç P2'den ikisi (BARIS-INTAKE-01, UI-METRIC-TRUNC-01) gerçek UX kusuruydu ve düzeltildi; biri (FAIR paketi) kod kusuru değil, P012 teslimatıdır. SEC-XFF ayrı bir savunma-derinliği kalemidir (kanıtlanmış güvenlik açığı DEĞİL); yine de repo örneğine uygulandı.

**Codex incelemesi düzeltmesi (SEC-XFF-01):** İlk raporda bu P1 "vulnerability" olarak sınıflanmıştı. Caddy'nin `reverse_proxy` varsayılanı istemci-verili `X-Forwarded-*` başlıklarını yok sayar (boş `trusted_proxies`), dolayısıyla shipped gateway varsayılan olarak spoof edilemez ve bulgu kanıtlanmış bir açık değildi. Açık `header_up` pin'i savunma-derinliği olarak korundu (ileride geniş bir `trusted_proxies` eklenirse de garanti sürsün). Yorum, README, validator kod adı (`P014_CADDY_FORWARDED_FOR_HARDENING_MISSING`) ve test adı buna göre düzeltildi.

## 4. Bulgu tablosu

| ID | Ağırlık | Ekran | Kanıt | Kullanıcı etkisi | Düzeltme | Retest |
|---|---|---|---|---|---|---|
| **SEC-XFF-01** | Savunma-derinliği (P1 DEĞİL) | Gateway (nginx + Caddy örneği) | `deploy/public-alpha/nginx.conf:27-52` rate/connection limitlerini `$http_x_forwarded_for`'a anahtarlıyor. Caddy varsayılanı istemci-verili XFF'i yok sayar (boş `trusted_proxies`), dolayısıyla shipped gateway varsayılan olarak spoof edilemez — bu **kanıtlanmış açık değil**, savunma-derinliği fırsatı. | Doğrudan yok (varsayılan Caddy korur). Yalnızca operatör ileride geniş bir `trusted_proxies` ayarlarsa risk oluşur. | Savunma-derinliği olarak Caddy örneğine `header_up X-Forwarded-For {http.request.remote.host}` (gerçek client IP'ye pin) eklendi; validator + test contract-lock; README savunma-derinliği notu. | `test_caddy_example_pins_forwarded_for_as_defense_in_depth` + validator; 24/24 deployment testi geçti. **Owner canlı merged Caddyfile'da geniş bir `trusted_proxies` OLMADIĞINI ve pin'in bulunduğunu teyit etmeli.** |
| **BARIS-INTAKE-01** | P2 (düzeltildi) | Corpus · Upload (red durumu) | Canlı kullanıcı (Barış Yücesan) `INGEST_INVALID_UTF8` aldı; yerelde birebir üretildi (`screenshots/intake-guidance-after-900.png`, `intake-guidance-clip-900.png`). `corpus.error.text` tek mesajı beş nedeni topluyordu ve yalnız teknik kod veriyordu; "tekrar dene" yönlendirmesi yoktu. Kullanıcı akışı bozuk sandı ve sayfayı yeniledi (repro: yenilemeye gerek yok — red sonrası widget temizleniyor, yeni dosya yüklemek çalışıyor). | Uzman kullanıcı hangi sorunun olduğunu ve ne yapacağını anlayamadı; app'i takılmış sandı. | INVALID_UTF8 ve MARKUP_DOCUMENT için neden-özel mesaj + eyleme dönük çözüm. Yönlendirme **hata sınıfına duyarlı**: kurtarılabilir kullanıcı-girdi hataları "başka dosya seç, yenileme gerekmez"; iç/workspace/cleanup hataları "sistem hatası... sürerse yenile" (Codex incelemesi düzeltmesi). | `test_common_beginner_rejections_...`, `test_recovery_guidance_separates_user_input_from_system_errors` (kurtarılabilir vs sistem, her iki dal), güncellenen `test_invalid_upload_...`; görsel red-mesajı ekranı doğrulandı. |
| **UI-METRIC-TRUNC-01** | P2 (düzeltildi) | Parameters (Guided özet) | `screenshots/metric-clip-before-1280.png`: "Display reference" = "500 ..." ve "Analysis unit" = "Whole..." kırpık. Kaynak `webapp.py:3422-3426` dört `st.metric`'i dar kolonda; Streamlit değeri ellipsis'liyor. | 1280-1440px masaüstünde iki özet metriği okunmuyor; render hatası gibi görünüyor (değerler alttaki tabloda mevcut ama özet kırpık). | `ui_theme.py`'a aşamaya-özel kural: `.st-key-parameters_stage [data-testid="stMetricValue"]` ve alt düğümleri wrap eder (kırpma yerine iki satır). Başka metrikler etkilenmez. | Masaüstü `screenshots/metric-wrap-after-1280.png` / `-1440.png`: tam okunuyor; DOM `white-space: normal`, kırpma yok. Mobil `screenshots/metric-375x844.png` (375×844): dört değer dikey yığılıp tam görünüyor, sayfa taşması yok. |
| FAIR-PKG-01 | P2 (makale-açığı) | Export yüzeyi | Tüm indirme butonları tek-artefakt JSON/CSV üretiyor; RO-Crate/.zenodo.json/DATA-SOURCES.csv/rights.json yok (CE-12 kapısı açık). | Yok (app doğru "FAIR-oriented" ve "reproducibility-oriented" fallback dilini kullanıyor). | Kod düzeltmesi DEĞİL — P012 teslimatı. Bölüm 7'de listelendi. | — |
| VIS-RAIL-01 | P3 (owner-kararı) | Review/Parameters masaüstü | `webapp.py:3664` non-upload aşamaları `st.columns([1.8,0.8])` böler; 0.8 kolon yalnız Method-boundary kartını taşır; parametre gridinin 4. sütunu 1280px'de kaydırmaya düşer. | Masaüstü genişliğinin ~%31'i kısa bir kartla dolarken tablolar daralıyor. | A5.1 onaylı ray'a dokunur — **owner kararı**. Düzeltilmedi. | — |
| A11Y-HEADING-01 | P3 | describe/review/prepare/results | `st.title` (h1) → `st.subheader` (h3), h2 atlanıyor (WCAG 1.3.1 başlık hiyerarşisi). Her görünümde tek H1 var (prob doğruladı), sorun yalnız seviye atlaması. | Ekran okuyucu gezintisinde başlık seviyesi atlaması. | Bölüm başlıklarını h2 yapmak + h3 boyutunu CSS'te korumak; dört görünümü ve görsel boyutu etkiler → görsel karar içerdiği için **owner onayına** bırakıldı. Düzeltilmedi. | — |
| CODE-DEAD-STRINGS-01 | P3 | catalog.py | Phase B öncesi ~32 kullanılmayan i18n anahtarı (evidence.*, run.*, map.*, sidebar.progress). | Yok (kullanıcıya görünmez). | Silme düşük değerli/hafif riskli; denetim PR'ını dar tutmak için ertelendi. | — |
| FAIR-CITATION-01 | P3 (makale-açığı) | CITATION.cff / codemeta.json | Release-bağlayıcı kimlik yok (repository-code, date-released, DOI, SWHID). | Yok. | P012 release'te eklenir. | — |
| FAIR-PINOCCHIO-01 | P3 (makale-açığı) | worked-example kanıtı | Yalnız plan belgeleri var; çalıştırılmış run paketi, DATA-SOURCES.csv, rights.json yok. | Yok. | P013 teslimatı. | — |
| FAIR-WALKTHROUGH-01 | P3 (makale-açığı) | değerlendirme kanıtı | expert-walkthrough-v1.md + defect-log.csv yok; ham prompt-events (45) ve human-decision (25) ledger'ları MEVCUT. | Yok. | P015 teslimatı. | — |
| FAIR-STABILITY-01 | P3 (makale-açığı) | prepare/parameters | P011 stability protokolü + calibration yok; app doğru biçimde Stable/Unstable etiketi YAYIMLAMIYOR, "Sensitivity check" / "parameter stability, not confidence" kullanıyor. | Yok. | P011 teslimatı. | — |

## 5. Çalıştırılan testler ve sonuçları

- `./scripts/verify.sh` (tüm düzeltmeler + Codex R1 sonrası): **1738 passed, 1 skipped** (belgeli macOS canonical-Linux R-worker skip), **%100 measured coverage** (11.697 statement, 3.052 branch), `metadata-ok`, `records-ok count=119`, `repository-scan-ok`, R-lock ok, `verify-ok`.
- Odaklı: `tests/test_p014_deployment.py` 24/24; `tests/test_intake_ui.py` (2 yeni test dahil); güncellenen `tests/test_webapp.py::test_invalid_upload_...`.
- **Taze-klon kaynak testi:** `--no-hardlinks` klon (HEAD `ce89a5a`), format temiz, deployment validator OK, dokunulan 45 test klondan geçti.
- Canlı read-only: home 200/`ok`, statik JS asset 200 (930KB — beyaz-ekran düzeltmesi çalışıyor), güvenlik başlıkları tam (CSP dış-host yok, X-Frame DENY, HSTS, no-referrer, COOP/CORP, Permissions-Policy), Server header sızmıyor, `via: Caddy`.
- Tam upload→R/stylo→results akışı: bu macOS hostta worker `/opt/renv/cache` gerektirdiği için `P009_PREPARED_CORPUS_RESULT_NOT_AVAILABLE` ile fail-closed olur (belgeli sınır). Results/Export yüzeyi canonical Linux CI ile doğrulanmıştır.
- **Otoritatif tam kapı:** bu dalın canonical Linux CI'sı (draft PR). Erişilebilirliğin otomatik kontrolü yapıldı; **VoiceOver/NVDA manuel testinin yerine geçmez.**

## 6. Manuel yapılması gereken testler

1. **Owner (savunma-derinliği, blocker değil):** canlı merged `/etc/caddy/Caddyfile` `delta.lemmata.app` bloğunun (a) istemciyi güvenen geniş bir `trusted_proxies` İÇERMEDİĞİNİ (Caddy varsayılanı zaten korur) ve (b) örnekteki `header_up X-Forwarded-For {http.request.remote.host}` pin'ini içerdiğini teyit et. Canlı dosya repoda değil; repo örneği güncellendi.
2. **Barış / manuel:** UTF-8 olmayan bir .txt yükleyip yeni yönlendirici mesajın göründüğünü ve yenilemeden yeni dosya yüklenebildiğini teyit et.
3. **Erişilebilirlik:** Safari + VoiceOver ve/veya NVDA ile Entry/Review/Parameters gezintisi (otomatik kontrol yeterli değil).
4. **Results/Export görseli:** canonical Linux ortamında bir kez insan gözüyle sonuç yüzeyi + export paketi kontrolü.

## 7. Makaleye başlamayı bekleyen bilimsel/kanıt açıkları (P011-P015)

Aşağıdakiler makale tasarımına başlamayı ENGELLEMEZ; makale tasarımının üreteceği kanıtlardır. Uygulama şu an her biri için doğru fallback dilini kullanıyor (claim-evidence-matrix bölüm 6 embargoları).

- **P011 (CE-08):** Parametre-stability protokolü + calibration. Stable/Partially-stable/Unstable etiketleri kanıt gelene dek yayımlanmaz; "parameter stability, not confidence" korunur.
- **P012 (CE-11, CE-12):** Tam FAIR-oriented run paketi (RO-Crate, .zenodo.json, DATA-SOURCES.csv, makine-okur rights.json, checksum manifesti, kilitli-ortam referansı, rerun README) + temiz-oda rerun. Geçene dek başlık/iddia "reproducibility-oriented" kalır; "reproducible" kullanılmaz. CITATION.cff/codemeta.json release-bağlayıcı kimlikleri (DOI/SWHID) burada eklenir.
- **P013 (CE-13, CE-16):** Pinokyo worked-example çalıştırılmış run paketi + asset-düzeyi rights.json + DATA-SOURCES.csv. Kanıt gelene dek Collodi/Pinokyo yalnız keşifsel örnek; "dönüm noktası" iddiası kurulmaz.
- **P015 (CE-17, CE-20):** Barış structured expert-walkthrough (expert-walkthrough-v1.md + defect-log.csv) ve scholarly-vibe-coding vaka raporu; mevcut prompt-events + human-decision ledger'larından sentezlenir. Bu iç QA'dir; genel usability/teachability iddiası kurulmaz.
- **Runtime AI (CE-18):** SBOM + config + secret taraması v0.1 runtime'ında LLM/dış AI çağrısı bulmuyor; production egress audit P014/P015'te tam kapanır.

## 8. Güçlü, korunması gereken kararlar (bilimsel dürüstlük)

Bilimsel-yöntem merceği SIFIR bulgu verdi (doğrulayarak, varsayarak değil): Classic Delta tanımı z-score mean-absolute-difference ile doğru; 500 MFW yapısal olarak "display reference" (en iyi değil); MFW/culling kopyası dürüst; unknown-holdout fitting-basis'e sızmıyor; stability ile confidence/probability ayrı; heatmap diyagonali beyaz + matris-içi ölçekli; nearest-neighbour 1e-12 tie toleransı + "yazar kimliği değil" siniri; confound matrisi + "kontrol etmez/kaldırmaz" fallback'i; yasak güçlü iddia (easy/proven/confidence/authorship proof/completely isolated/reproducible) hiçbir kullanıcı-görünür string'de yok.

## 9. Karar

**CONDITIONAL GO** — makale tasarımına başlanabilir. **P0/P1 blocker yok.** Koşullar: (a) owner canlı Caddyfile'da geniş bir `trusted_proxies` olmadığını ve XFF pin'inin bulunduğunu teyit etmeli (savunma-derinliği); (b) düzeltilen iki P2 + savunma-derinliği kalemi PR review + green CI'dan geçmeli. Hiçbiri makale tasarımına başlamayı engellemez. P011-P015 kapıları AÇIK sınırlardır ve makalenin bu turda hazır olduğu iddia edilmez.

## 10. Canlı tasarım denetimi takibi (2026-07-19)

Denetim sonrası canlı `delta.lemmata.app` uzman gözle incelendi ve aile
siteleriyle (`lemmata.app`, `lda.lemmata.app`) görsel tutarlılık için altı
tasarım düzeltmesi uygulandı; A5.1 sistemi içinde kalındı. İkinci turda mobil
boşluk/padding ve header kenar adayları DOM ile ölçülüp gerçek sorun olmadığı
doğrulandı (uydurma değişiklik yapılmadı). Üçüncü turda (owner sorusu) canlı
LDA + lemmata.app'e karşı computed-style tipografi ölçümü yapıldı: gövde LDA
ile birebir aynı; mikro-etiketler 12px'e çekildi, giriş ekranındaki üçlü mesaj
tekrarı temizlendi, sidebar sayaç tonları WCAG metin-token'larına alındı
(ayrıntı: `design-review/README.md` Düzeltme 5-6). Dördüncü turda sonuç ekranı
sentetik ResultViewV1 ile denetlendi: kare MDS grafiğinin Streamlit 360px
slotunu taşırıp koordinat tablosunun altında unknown-holdout noktasını (D04)
gizlediği bindirme bugı düzeltildi; heatmap/MDS etiketleri "sigla · başlık"
biçimiyle tutarlılaştırıldı (pinli semantic tablolar ve canonical export
değişmedi); mobil purpose-rehberi seçimin ardına taşındı; deploy README'deki
sabit IP `DELTA_HOST` değişkenine çekildi (Düzeltme 7-8).
- Header build SHA'sı 12 karaktere kısaltıldı, tam SHA `title` ipucunda.
- Review kenar çubuğundaki boş kolon aşamaya duyarlı "Preparation summary"
  ile dolduruldu (canlı sayaçlar + evidence listesi; ölü `evidence.*`
  metinleri yeniden kullanıma alındı).
- Deney haritası (stepper) aktif adım göstergesi düzeltildi: teal üst çizgi kutu
  kenarının üstünde havada duruyordu; `overflow: hidden` + inset teal aksan +
  `--delta-mint` wash ile net "aktif sekme"ye çevrildi, Streamlit `<li>` stray
  margin'i sıfırlandı, hücreler hizalandı.
- Sidebar evidence satırları uniform stacked ledger'a çevrildi: yalnız
  "Parameter sensitivity" satırı çift satıra kırılıp dengesizdi; ad üstte / durum
  altta stack ile tüm satırlar tutarlı iki satır oldu (anlam korundu).

Yeni özellik/runtime AI/login/analytics yok; Classic Delta/MFW/önişleme/yorum
sınırları değişmedi. Kanıt: `provenance/evidence/P014/design-review/`
(before/after görseller + `MANIFEST.sha256`). Testler +5, `verify.sh` yeşil,
%100 kapsam. Commit'ler `be5ccf3` (kod+test) ve `3b3a460` (kanıt), PR #15
(draft) üzerinde; canlı sunucuya dağıtım yapılmadı.
