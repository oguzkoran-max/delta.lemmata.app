# P014 Canlı Public-Alpha Kapsamlı Denetim ve Düzeltme

**Tarih:** 2026-07-18
**Denetleyen:** Claude Code (Opus 4.8), yedi bağımsız mercek + adversaryel sentez
**Amaç:** Makale yazımına başlamadan önce canlı `delta.lemmata.app` public-alpha sürümünün genel denetimi, doğrulanan sorunların düzeltilmesi ve makale için kalan bilimsel kanıt açıklarının belirlenmesi. Bu belge makalenin gönderime hazır olduğunu iddia etmez.

## 1. Kapsam ve ortam

- **Başlangıç SHA:** `3cfe0713a7159fcbedb0c390e801698dd09ae77d` (origin/main)
- **Denetim dalı:** `claude/p014-pre-manuscript-audit` (origin/main'den açıldı)
- **Bitiş SHA (düzeltmeler sonrası):** `ce89a5a5a655ee2725e7eb05bd2c8b951e08c3a9`
- **Canlı Delta:** `https://delta.lemmata.app` — home HTTP 200, `/_stcore/health` = `ok`
- **Aynı VPS'teki LDA:** `https://lda.lemmata.app` — home 200, health `ok` (yalnız read-only gözlem; değişmedi)
- **Yerel doğrulama:** `./scripts/verify.sh` düzeltmeler öncesi ve sonrası geçti; taze klon kaynak testi yapıldı
- **Test corpus'u:** yalnız depo içi sentetik fixture; kullanıcıya ait gerçek metin kullanılmadı

Çalışma ağacı denetim başında temizdi (kullanıcı değişikliği yoktu). Hiçbir canlı sunucu, Caddy, DNS, Docker registry veya LDA dosyasına dokunulmadı.

## 2. Yönetici kararı

**CONDITIONAL GO** — makale *tasarımına* başlanabilir.

Uygulama yüzeyi bilimsel olarak dürüst ve tutarlı; canlı altyapı sağlıklı ve güvenli başlıklarla korunuyor. Bu turda bulunan tek P1 (gateway rate-limit atlatma) ve iki masaüstü P2 kusuru bu dalda düzeltildi ve testlendi. Kalan açıkların tamamı P011/P012/P013/P015 için zaten *üretilecek* kanıt kalemleridir (makale tasarımının kendisi bunları üretecek). Bu karar yalnız "makale tasarımına başlayabilir miyiz?" sorusuna cevap verir; P011-P015 kapılarının tamamlandığını veya sürümün gönderime hazır olduğunu söylemez.

## 3. Bulunan sorun sayıları

| Ağırlık | Adet | Bu turda düzeltilen | Ertelenen |
|---|---|---|---|
| P0 (kullanılamaz/yanıltıcı) | 0 | 0 | 0 |
| P1 (ana akış/güvenlik/ciddi erişilebilirlik) | 1 | **1** | 0 |
| P2 (profesyonel kalite kaybı, yayın-engeli değil) | 4 | **3** | 1 (makale-açığı) |
| P3 (küçük cila / gelecek) | 7 | 0 | 7 |

P2 dörtten biri (FAIR paketi) bir kod kusuru değil, P012 teslimatıdır. Üç P2 gerçek kod/kopya kusuruydu ve düzeltildi.

## 4. Bulgu tablosu

| ID | Ağırlık | Ekran | Kanıt | Kullanıcı etkisi | Düzeltme | Retest |
|---|---|---|---|---|---|---|
| **SEC-XFF-01** | P1 | Gateway (nginx + Caddy örneği) | `deploy/public-alpha/nginx.conf:27-52` rate/connection limitlerini `$http_x_forwarded_for` tam string'ine anahtarlıyor; shipped `Caddyfile.delta.example` XFF'i *replace* etmiyordu (Caddy istemci-verili değeri koruyup gerçek IP'yi ekliyor). | Saldırgan XFF önekini döndürerek per-client istek-hızı (120r/m) ve eşzamanlı bağlantı (20) limitlerini aşabilir; paylaşımlı VPS'te Lemmata'ya kaynak sıçraması riski. | Caddy örneğine `header_up X-Forwarded-For {http.request.remote.host}` eklendi (edge XFF'i gerçek client IP ile değiştirir); deployment validator + test contract-lock yaptı; README canlı merged Caddyfile için operatör notu aldı. | `test_caddy_example_replaces_forwarded_for_so_rate_limits_are_not_spoofable` + validator; 24/24 deployment testi geçti. **Owner canlı merged Caddyfile'da bu satırın (veya `trusted_proxies`) mevcut olduğunu teyit etmeli.** |
| **BARIS-INTAKE-01** | P2 | Corpus · Upload (red durumu) | Canlı kullanıcı (Barış Yücesan) `INGEST_INVALID_UTF8` aldı; yerelde birebir üretildi. `corpus.error.text` tek mesajı beş nedeni topluyordu ("empty / not valid UTF-8 and NFC / unsafe controls / markup") ve yalnız teknik kod veriyordu; "tekrar dene" yönlendirmesi yoktu. Kullanıcı akışı bozuk sandı ve sayfayı yeniledi (oysa yenilemeye gerek yok — repro: red sonrası widget temizleniyor, yeni dosya yüklemek çalışıyor). | Uzman kullanıcı hangi sorunun olduğunu ve ne yapacağını anlayamadı; app'i takılmış sandı. | INVALID_UTF8 → "This file is not saved as UTF-8 text. Re-save it as plain UTF-8... and upload it again."; MARKUP_DOCUMENT → "...save it as a plain .txt file and upload it again."; her redde "You can choose another file and try again without reloading the page." satırı eklendi. | `test_common_beginner_rejections_get_cause_specific_guidance`, `test_every_intake_error_message_resolves_...`, güncellenen `test_invalid_upload_is_rejected_...`; repro görsel + metin doğrulandı. |
| **UI-METRIC-TRUNC-01** | P2 | Parameters (Guided özet) | `screenshots/metric-clip-before-1280.png`: "Display reference" = "500 ..." ve "Analysis unit" = "Whole..." kırpık. Kaynak `webapp.py:3422-3426` dört `st.metric`'i dar kolonda; Streamlit değeri ellipsis'liyor. | 1280-1440px masaüstünde iki özet metriği okunmuyor; render hatası gibi görünüyor (değerler alttaki tabloda mevcut ama özet kırpık). | `ui_theme.py`'a aşamaya-özel kural: `.st-key-parameters_stage [data-testid="stMetricValue"]` ve alt düğümleri wrap eder (kırpma yerine iki satır). Başka metrikler etkilenmez. | `screenshots/metric-wrap-after-1280.png` / `-1440.png`: "500 MFW" ve "Whole text" tam okunuyor; DOM ölçümü `white-space: normal`, kırpma yok. |
| FAIR-PKG-01 | P2 (makale-açığı) | Export yüzeyi | Tüm indirme butonları tek-artefakt JSON/CSV üretiyor; RO-Crate/.zenodo.json/DATA-SOURCES.csv/rights.json yok (CE-12 kapısı açık). | Yok (app doğru "FAIR-oriented" ve "reproducibility-oriented" fallback dilini kullanıyor). | Kod düzeltmesi DEĞİL — P012 teslimatı. Bölüm 7'de listelendi. | — |
| VIS-RAIL-01 | P3 (owner-kararı) | Review/Parameters masaüstü | `webapp.py:3664` non-upload aşamaları `st.columns([1.8,0.8])` böler; 0.8 kolon yalnız Method-boundary kartını taşır; parametre gridinin 4. sütunu 1280px'de kaydırmaya düşer. | Masaüstü genişliğinin ~%31'i kısa bir kartla dolarken tablolar daralıyor. | A5.1 onaylı ray'a dokunur — **owner kararı**. Düzeltilmedi. | — |
| A11Y-HEADING-01 | P3 | describe/review/prepare/results | `st.title` (h1) → `st.subheader` (h3), h2 atlanıyor (WCAG 1.3.1 başlık hiyerarşisi). Her görünümde tek H1 var (prob doğruladı), sorun yalnız seviye atlaması. | Ekran okuyucu gezintisinde başlık seviyesi atlaması. | Bölüm başlıklarını h2 yapmak + h3 boyutunu CSS'te korumak; dört görünümü ve görsel boyutu etkiler → görsel karar içerdiği için **owner onayına** bırakıldı. Düzeltilmedi. | — |
| CODE-DEAD-STRINGS-01 | P3 | catalog.py | Phase B öncesi ~32 kullanılmayan i18n anahtarı (evidence.*, run.*, map.*, sidebar.progress). | Yok (kullanıcıya görünmez). | Silme düşük değerli/hafif riskli; denetim PR'ını dar tutmak için ertelendi. | — |
| FAIR-CITATION-01 | P3 (makale-açığı) | CITATION.cff / codemeta.json | Release-bağlayıcı kimlik yok (repository-code, date-released, DOI, SWHID). | Yok. | P012 release'te eklenir. | — |
| FAIR-PINOCCHIO-01 | P3 (makale-açığı) | worked-example kanıtı | Yalnız plan belgeleri var; çalıştırılmış run paketi, DATA-SOURCES.csv, rights.json yok. | Yok. | P013 teslimatı. | — |
| FAIR-WALKTHROUGH-01 | P3 (makale-açığı) | değerlendirme kanıtı | expert-walkthrough-v1.md + defect-log.csv yok; ham prompt-events (45) ve human-decision (25) ledger'ları MEVCUT. | Yok. | P015 teslimatı. | — |
| FAIR-STABILITY-01 | P3 (makale-açığı) | prepare/parameters | P011 stability protokolü + calibration yok; app doğru biçimde Stable/Unstable etiketi YAYIMLAMIYOR, "Sensitivity check" / "parameter stability, not confidence" kullanıyor. | Yok. | P011 teslimatı. | — |

## 5. Çalıştırılan testler ve sonuçları

- `./scripts/verify.sh` (düzeltmeler sonrası): **1737 passed, 1 skipped** (belgeli macOS canonical-Linux R-worker skip), **%100 measured coverage** (11.693 statement, 3.050 branch), `metadata-ok`, `records-ok count=119`, `repository-scan-ok`, R-lock ok, `verify-ok`.
- Odaklı: `tests/test_p014_deployment.py` 24/24; `tests/test_intake_ui.py` (2 yeni test dahil); güncellenen `tests/test_webapp.py::test_invalid_upload_...`.
- **Taze-klon kaynak testi:** `--no-hardlinks` klon (HEAD `ce89a5a`), format temiz, deployment validator OK, dokunulan 45 test klondan geçti.
- Canlı read-only: home 200/`ok`, statik JS asset 200 (930KB — beyaz-ekran düzeltmesi çalışıyor), güvenlik başlıkları tam (CSP dış-host yok, X-Frame DENY, HSTS, no-referrer, COOP/CORP, Permissions-Policy), Server header sızmıyor, `via: Caddy`.
- Tam upload→R/stylo→results akışı: bu macOS hostta worker `/opt/renv/cache` gerektirdiği için `P009_PREPARED_CORPUS_RESULT_NOT_AVAILABLE` ile fail-closed olur (belgeli sınır). Results/Export yüzeyi canonical Linux CI ile doğrulanmıştır.
- **Otoritatif tam kapı:** bu dalın canonical Linux CI'sı (draft PR). Erişilebilirliğin otomatik kontrolü yapıldı; **VoiceOver/NVDA manuel testinin yerine geçmez.**

## 6. Manuel yapılması gereken testler

1. **Owner:** canlı merged `/etc/caddy/Caddyfile` `delta.lemmata.app` bloğunun `header_up X-Forwarded-For {http.request.remote.host}` (ya da `trusted_proxies`) içerdiğini teyit et; yoksa canlıya açılmadan ekle. SEC-XFF-01 repo örneğinde kapatıldı, canlı dosya repoda değil.
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

**CONDITIONAL GO** — makale tasarımına başlanabilir. Koşullar: (a) owner canlı Caddyfile'ın XFF'i replace ettiğini canlıya açılmadan teyit etmeli; (b) düzeltilen üç kusur PR review + green CI'dan geçmeli. Hiçbiri makale tasarımına başlamayı engellemez. P011-P015 kapıları AÇIK sınırlardır ve makalenin bu turda hazır olduğu iddia edilmez.
