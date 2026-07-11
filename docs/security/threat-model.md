# Delta Threat Model

**Durum:** P000 tasarım tabanı  
**Tarih:** 2026-07-10  
**Kapsam:** v0.1 browser uygulaması, Python/Streamlit orchestration, R `stylo` worker, export paketi, ortak VPS üzerindeki dağıtım ve makale kanıt zinciri  
**Kapsam dışı:** Runtime AI, kullanıcı hesabı, kalıcı proje depolama ve ödeme sistemi v0.1'de yoktur.

## 1. Amaç

Bu belge yalnız sunucu güvenliğini değil, bilimsel sonucun yanlış güven üretmesini de tehdit olarak ele alır. Delta için güvenli bir koşum şu dört özelliği birlikte sağlamalıdır:

1. Yüklenen içerik başka oturuma, loga, export'a veya kalıcı depoya sızmaz.
2. Kullanıcı girdisi Python, R, shell veya dosya sistemi üzerinde yetkisiz işlem yaptıramaz.
3. Dağıtılan veri ve yazılım, hak ve lisans koşullarına uygundur.
4. Arayüz, yöntemin desteklemediği kesinlik, nedensellik veya genellenebilirlik izlenimi üretmez.

Bu belge bir güvenlik sertifikası değildir. Her kontrol, ilgili ticket'ta çalıştırılmış bir test ve saklanmış kanıtla doğrulanana kadar `planned` durumundadır.

## 2. Korunacak Varlıklar

| Varlık | Koruma hedefi |
|---|---|
| Kullanıcı ham metinleri ve metadata | Gizlilik, oturum izolasyonu, zamanında silme |
| Normalize edilmiş ve segmentlenmiş metin | Gizlilik, bütünlük, kaynak ham metinle izlenebilirlik |
| Analiz parametreleri ve sonuçları | Bütünlük, tekrar çalıştırılabilirlik, doğru sürüm bağı |
| R worker ve Python orchestration | Komut enjeksiyonuna, kaynak taşmasına ve bağımlılık sapmasına direnç |
| Export paketi | Tamlık, checksum doğruluğu, hak bilgisinin varlık düzeyinde korunması |
| Benchmark ve Pinokyo corpus'u | Leakage, edition/OCR, duplicate ve hak risklerinden korunma |
| Claim-evidence kaydı | Ürün ve makale iddialarının kanıt kapılarına bağlı kalması |
| Lemmata servisi ve ortak VPS | Delta kaynak taşmasının veya ihlalinin diğer servise yayılmaması |
| PromptEvent, Ticket, HumanDecision, Commit, ADR ve Run provenance'ı | Doğruluk, insan/AI sahiplik ayrımı, native ve reconstructed kayıtların karışmaması |

## 3. Güven Sınırları

| ID | Sınır | Sınırı geçen veri | Varsayılan tutum |
|---|---|---|---|
| TB-01 | İnternet ve reverse proxy | HTTP istekleri, dosya upload'u | Tamamen güvensiz |
| TB-02 | Reverse proxy ve Streamlit uygulaması | Doğrulanmış boyut/protokol sonrası istek | Yeniden doğrula |
| TB-03 | Parser ve koşuma özel workspace | Dosya adı, archive üyeleri, metin, metadata | Temizle, sınırla, yeniden adlandır |
| TB-04 | Python orchestration ve R worker | Yapılandırılmış parametreler, corpus yolu | Shell kullanma; allowlist şema kullan |
| TB-05 | Sonuç nesnesi ve export builder | Tablo, grafik, manifest, opsiyonel metin | Şemaya göre üret; içerik kapsamını doğrula |
| TB-06 | Delta container'ı ve Lemmata altyapısı | CPU, RAM, disk, ağ, proxy | Ayrı servis kimliği ve kaynak sınırı |
| TB-07 | Build ortamı ve runtime image | Paketler, lockfile, image, SBOM | Pinlenmiş ve doğrulanmış girdiler |
| TB-08 | İç corpus ve kamu release'i | Metin, metadata, rights manifest | Asset-level yayın kapısı |
| TB-09 | Calibration, locked evaluation ve Pinokyo | Eşikler, grid, benchmark sonuçları | Aşama ayrımı ve sızıntı denetimi |

## 4. Risk Ölçeği

- **Critical:** Gizli metin sızıntısı, uzaktan kod çalıştırma, servisler arası yayılma, bilimsel değerlendirme sızıntısı veya hak ihlali doğurabilir. İlgili release kapısı kapanır.
- **High:** Sonucu ciddi biçimde bozabilir, hizmeti kesebilir veya makale iddiasını geçersiz kılabilir. Yayın öncesi çözülür.
- **Medium:** Savunma derinliği, açıklık veya nadir hata senaryosudur. Açık kalırsa gerekçe ve sınırlama kaydı gerekir.

Risk, yalnız olasılığa göre düşürülmez. Kullanıcı metni, hak ihlali ve epistemik yanlış güven için etkinin ağırlığı önceliklidir.

## 5. Uygulama ve Altyapı Tehditleri

| ID | Risk | Tehdit ve başarısızlık biçimi | Zorunlu kontrol | Doğrulama kanıtı | Ticket |
|---|---|---|---|---|---|
| SEC-01 | High | Binary, polyglot, bozuk encoding, aşırı uzun token veya yanıltıcı uzantı parser'ı ve belleği zorlar. | İçerik tabanlı tür kontrolü; UTF-8 politikası; karakter, token ve satır sınırları; fail-closed parser | Kötücül upload fixture seti ve parser test raporu | P003 |
| SEC-02 | Critical | Archive path traversal, absolute path, symlink, hardlink veya iç içe archive workspace dışına yazar. | Archive üyelerini önceden listele; canonical path kontrolü; link ve nested archive reddi; yalnız yeni, koşuma özel dizine çıkar | Zip-slip ve link fixture testleri | P003 |
| SEC-03 | Critical | Zip bomb veya sıkıştırma oranı saldırısı disk ve belleği tüketir. | Sıkıştırılmış/açılmış boyut, üye sayısı, derinlik ve oran limiti; streaming sayaç; kota aşımında atomik iptal | Bomb fixture ve disk kota testi | P003, P005 |
| SEC-04 | High | Unicode normalization, case folding, reserved names veya TOCTOU ile dosya çakışması oluşur. | Sunucu üretimli kimlik; kullanıcı adını yol olarak kullanmama; NFC kontrolü; `O_EXCL`; duplicate-name raporu | Unicode ve çakışma test matrisi | P003 |
| SEC-05 | High | Dosya adı, metadata veya analiz çıktısı CSV formula, log, newline, path ya da HTML enjeksiyonu taşır. | Context-aware escaping; kontrollü display label; CSV formül nötralizasyonu; yapılandırılmış log; HTML sanitization | Injection fixture E2E ve export testi | P003, P009, P012 |
| SEC-06 | Critical | Parametre veya dosya adı R koduna ya da shell komutuna dönüşür. | Shell interpolation yok; sabit R entrypoint; JSON/CLI şeması; enum ve sayısal allowlist; worker düşük yetkili kullanıcı | Command-injection testi ve wrapper code audit | P006 |
| SEC-07 | Critical | R worker fork, sonsuz koşum, ağ erişimi veya bellek/CPU taşması yaratır. | Container/process isolation; wall-clock timeout; CPU/RAM/PID limiti; read-only root; no-new-privileges; egress deny; process-tree kill | Timeout, fork, OOM ve egress-denied testleri | P005, P006, P014 |
| SEC-08 | High | Bozuk, eksik veya beklenmeyen worker çıktısı yanlış sonuç gibi gösterilir. | Versioned result schema; finite-number ve cardinality kontrolü; fail-closed state; partial result etiketi | Malformed-output contract testleri | P006, P009 |
| SEC-09 | Critical | Session, cache veya tahmin edilebilir job kimliği bir kullanıcının verisini başkasına gösterir. | Kriptografik job ID; server-side ownership binding; koşuma özel dizin/cache; global mutable state yok; cross-session test | İki eşzamanlı oturum izolasyon raporu | P005, P014 |
| SEC-10 | Critical | Export, raw metinleri, temp yollarını, stack trace'i veya başka koşumun dosyalarını sızdırır. | Export allowlist; package manifestinden üretim; raw default-off; absolute path redaction; package öncesi content scan | Canary metin ve path-leak testi | P012 |
| SEC-11 | High | Loglar metin içeriği, token, dosya yolu veya kişisel metadata saklar. | Content-free structured log; alan allowlisti; secret redaction; 7 günlük rotasyon; erişim sınırı | Log canary taraması ve retention kanıtı | P005, P014 |
| SEC-12 | Critical | Başarılı/başarısız iş artıkları, reboot, crash, swap, snapshot veya backup içinde kalır. | Başarıda export sonrası silme; hatada en çok 15 dakika; disk export en çok 1 saat; startup janitor; swap/backup politikası; ephemeral workspace | Crash/reboot cleanup ve disk tarama raporu | P005, P014 |
| SEC-13 | High | Büyük veya tekrarlı işler queue ve kaynakları tüketir. | Dosya/job/grid limitleri; eşzamanlılık sınırı; queue backpressure; proxy rate limit; reddedilen işte kaynak ayırmama | Load ve abuse testi | P005, P014 |
| SEC-14 | High | Yanlış proxy/TLS/CORS/Host/CSRF/clickjacking ayarı oturumu veya isteği kötüye açar. | TLS; strict Host; güvenli headers; dar CORS; CSRF uyumlu deployment; request-size limit | Header ve proxy config testi | P014 |
| SEC-15 | Critical | Delta ihlali veya kaynak taşması aynı VPS'teki Lemmata'ya yayılır. | Ayrı container, kullanıcı, network, volume, env, port ve secret; CPU/RAM/disk quota; yalnız proxy üzerinden erişim; Lemmata smoke monitor | Delta stresinde Lemmata smoke testi ve izolasyon denetimi | P014 |
| SEC-16 | Critical | Bağımlılık veya image tedarik zinciri kötü niyetli ya da yeniden üretilemez artifact getirir. | Python ve R lock; digest-pinned base image; SBOM; vulnerability ve secret scan; kontrollü update; signed release tercih edilir | Lock doğrulama, SBOM ve scan raporu | P001, P014, P015 |

## 6. Haklar, FAIR ve Tekrar Üretim Tehditleri

| ID | Risk | Tehdit ve başarısızlık biçimi | Zorunlu kontrol | Doğrulama kanıtı | Ticket |
|---|---|---|---|---|---|
| RP-01 | Critical | Corpus düzeyinde genel etiket, tek tek metinlerin farklı hak durumunu örter. | Her asset için source, edition, jurisdiction, rights status, license, allowed actions ve evidence URL; `unknown` varsayılanı | Asset-level rights manifest validator | P004, P013 |
| RP-02 | Critical | Kullanıcı beyanı veya source license, metni yeniden dağıtma hakkı varmış gibi yorumlanır. | Upload izni ile public redistribution iznini ayır; raw export ve public bundle için ayrı kapı; belirsizde kapalı | Rights decision log ve negative fixtures | P004, P012, P013 |
| RP-03 | High | Hak kanıtı linki değişir veya kaybolur. | Access date, snapshot/hash veya kalıcı tanımlayıcı; karar gerekçesi; periyodik link check | Rights-link audit raporu | P013, P015 |
| RP-04 | High | Manifest başarısız grid hücrelerini, varsayılanları veya preprocessing ayrıntısını saklar. | Başarılı ve başarısız tüm hücreler; resolved defaults; input inventory; warning ve error kayıtları | Export completeness validator | P012 |
| RP-05 | High | Paket sürümü, locale, BLAS, sıralama, seed veya bağımlılık sapması sonucu değiştirir. | Lockfiles; image digest; session info; locale/timezone; deterministic ordering; seed kaydı; toleranslı parity testi | İki temiz ortam rerun karşılaştırması | P006, P012, P015 |
| RP-06 | High | Raw metni paylaşmamak gizliliği korur fakat gerçek tekrar koşumu imkansız bırakabilir. | `reproducibility level` alanı; checksums ve acquisition recipe; yeniden dağıtılabilir corpus için opsiyonel ayrı paket; iddiayı seviyeye bağla | Package-level reproducibility sınıflandırması | P012, P015 |
| RP-07 | High | Export paketi sonradan değiştirilir veya dosyalar karışır. | SHA-256 manifest; self-check komutu; release checksum; immutable release tag | Tamper testi ve checksum raporu | P012, P015 |
| RP-08 | High | Site, makale, Git tag, DOI, SWHID ve container farklı sürümleri gösterir. | Tek release manifesti; VERSION kaynağı; metadata consistency check | Cross-surface version audit | P001, P015 |
| RP-09 | High | AI geliştirme kaydı eksik olduğu halde tam, exact veya native provenance gibi sunulur. | PromptEvent kayıt modu; hash; gap kaydı; reconstructed/native ayrımı; disclosure | Provenance coverage raporu | P001-P015 |

## 7. Epistemik Tehditler

| ID | Risk | Tehdit ve başarısızlık biçimi | Zorunlu kontrol | Doğrulama kanıtı | Ticket |
|---|---|---|---|---|---|
| EPI-01 | High | Yanlış author/date/genre etiketi, paratext veya kasıtlı corpus poisoning sonucu yönlendirir. | Metadata schema; source provenance; corpus inventory; paratext audit; label validation | Corpus-health report | P004, P007, P013 |
| EPI-02 | High | Aynı edition, duplicate eser veya tekrar kullanılan pasaj train/test bağımsızlığı izlenimi yaratır. | Exact ve near-duplicate taraması; edition ID; shared-passage uyarısı; grup bağımlılığı | Duplicate audit ve fixture testleri | P007, P010, P013 |
| EPI-03 | Critical | Unknown metin veya ondan türetilen bilgi preprocessing, feature selection, scaling ya da calibration'a sızar. | Pipeline sırasını kilitle; holdout isolation; unknown-free fitting; leakage canary | Leakage test raporu | P006, P010 |
| EPI-04 | High | Segmentler bağımsız gözlem sayılır veya uzun eserler sonucu domine eder. | Work-level split; author/work-aware aggregation; segment count ve weighting raporu; uncertainty unit açıklaması | Segment/permutation benchmark | P007, P010, P011 |
| EPI-05 | High | Güzel görünen MFW/culling/distance hücreleri seçilir, başarısız hücreler saklanır. | Önceden ilan edilmiş grid; 24-cell public cap; 192-cell controlled batch; tüm hücreleri export; post-hoc değişikliği kaydet | Grid manifest ve completeness check | P011, P012 |
| EPI-06 | Critical | Edition, OCR veya normalization farkı yazar zamanı gibi görünür. | Edition-aware metadata; OCR kalite alanı; normalization diff summary; confound warning; sensitivity run | Diachronic benchmark ve Pinokchio audit | P007, P010, P013 |
| EPI-07 | High | Genre, audience, publisher veya chronology confound'u stil değişimi gibi yorumlanır. | Confound inventory; balanced/stratified comparison mümkünse; negative control; warning language | Diachronic benchmark ve worked-example report | P010, P013 |
| EPI-08 | Critical | Parameter stability, doğruluk veya yazarlık olasılığı diye sunulur. | `stability, not confidence` dili; benchmark-calibrated eşik; explanation contract; claim-lint | UI copy snapshot, threshold calibration report | P009, P011 |
| EPI-09 | Critical | Benchmark veya Pinokyo sonuçları eşik ve yöntem seçimini etkileyip sonra bağımsız test diye sunulur. | Development, calibration, locked evaluation ve worked example ayrımı; immutable split hash; change log | Split registry ve contamination audit | P010, P011, P013 |
| EPI-10 | High | Unknown her durumda en yakın yazara zorlanır ve attribution gibi okunur. | Open-set sınır dili; distance/proximity output; abstention veya `insufficient support`; kesin yazar etiketi yok | Unknown scenario acceptance testleri | P008, P009, P010 |
| EPI-11 | High | Çok küçük veya dengesiz corpus güvenilir grafik üretir. | Minimum data gates; corpus-health severity; analizi durdurma koşulları; feature/sample uyarısı | Boundary fixture suite | P007, P009 |
| EPI-12 | High | Distance ortalaması, grid hücreleri veya segment permütasyonu sahte örneklem büyüklüğü yaratır. | Bağımsızlık birimini work/author düzeyinde tanımla; hücreleri tekrar ölçüm olarak ele al; yöntem notu | Statistical design review | P010, P011, P015 |
| EPI-13 | High | Tek uzman walkthrough'u veya scholarly vibe coding vakası, genel usability, programlama uzmanlığının gereksizliği ya da bilimsel geçerlilik kanıtı gibi sunulur. | Barış değerlendirmesini structured expert walkthrough olarak sınırla; araştırma katılımcısı yok; AI ajanları yazar değil; HumanDecision ledger; transferability claim'i yok; iddia denylisti | Walkthrough protocol, human-decision ledger, contribution statement, manuscript claim audit | P001, P015 |

### P001 Kontrol Durumu

| Threat | Durum | P001 kontrolü | Kalan doğrulama |
|---|---|---|---|
| SEC-16 | `implemented` | Python/R lock, digest-pinned base, action SHA lock, SBOM, vulnerability ve secret scan | Container build, signed/public release ve P014/P015 supply-chain audit |
| RP-08 | `implemented` | VERSION, package, citation ve CodeMeta metadata consistency testi | Site/tag/container/DOI/SWHID içeren P015 cross-surface release audit |
| RP-09 | `implemented` | Native request hash'i, summary-only response ayrımı ve commit-linked P001 PromptEvent | P002-P015 tam coverage raporu ve final disclosure audit |
| EPI-13 | `implemented` | HumanDecision rol ayrımı, no-code claim sınırı ve site/makale denylisti | Barış walkthrough, contribution statement ve P015 manuscript claim audit |

Buradaki `implemented`, riskin kapandığı anlamına gelmez. P001 yalnız zorunlu kontrol
altyapısını kurmuştur; ilgili son ticket kanıtı olmadan `verified` kullanılmaz.

### P002 Kontrol Durumu

| Threat | Durum | P002 kontrolü | Kalan doğrulama |
|---|---|---|---|
| SEC-14 | `not verified` | Streamlit XSRF/CORS korumaları açık ve shell yalnız loopback üzerinde test edildi | TLS, strict Host, headers, proxy, request-size ve deployment CSRF testlerinin tamamı P014 |
| EPI-13 | `implemented` | Merkezi claim denylisti, kapsam sınırı, insan/AI rol ayrımı ve başarısız kontrollerin P002 kanıtında saklanması | Barış structured walkthrough, contribution statement ve P015 manuscript claim audit |

P002 ağ-kapalı testi production güvenlik doğrulaması değildir. SEC-14 bu nedenle
geçmiş veya `verified` olarak işaretlenmez.

### P003 Kontrol Durumu

| Threat | Durum | P003 kontrolü | Kalan doğrulama |
|---|---|---|---|
| SEC-01 | `verified: application intake` | Açık rol, uzantı, varsa MIME, katı UTF-8/NFC, belge imzası, karakter, satır ve token sınırları; sabit ve üretilmiş fixture'lar | Proxy request buffering ve production kaynak sınırları P014 |
| SEC-02 | `verified: application intake` | Ham ZIP header ön kontrolü, canonical path, link/device/nested archive reddi, hedef oluşturmadan tam inventory | Crash/restart ve production filesystem davranışı P005/P014 |
| SEC-03 | `implemented; partially verified` | Sürümlü member, byte, expanded byte ve ratio limitleri; streaming sayaç ve deterministic bomb fixture'ları | OS/container kota, OOM, timeout ve eşzamanlı yük P005/P014 |
| SEC-04 | `verified: application intake` | NFC/casefold collision, reserved name, server ID, düz storage adı, `O_EXCL` ve no-follow yazma | Multi-process/container yarışı ve production volume P005/P014 |
| SEC-05 | `implemented: intake only` | Kontrollü display label; CSV formula, HTML, newline ve path benzeri hücre reddi; content-free hata | Analiz çıktısı ve export escaping P009/P012 |

P003 ara kanıtı `provenance/evidence/P003/` altındaki parser raporu, fixture ve
fuzz özetleri, cleanup kapsamı, browser audit ve exact-commit clean-clone kaydı ile
`RUN-20260711-0003` ve dış checksum manifestidir. Bu ara
durumlar SEC-03 veya SEC-05'in bütün release yüzeylerinde kapandığı anlamına
gelmez. Özellikle SEC-12 ve CE-14 P005/P014/P015 kanıtı olmadan `verified`
olarak işaretlenmez.

## 8. Release Kapıları

### Public Beta Kapısı

Şu riskler test kanıtıyla kapanmadan kamuya açık upload servisi açılmaz:

- SEC-02 archive traversal
- SEC-03 archive bomb
- SEC-06 R ve shell injection
- SEC-07 worker resource ve egress isolation
- SEC-09 cross-session isolation
- SEC-10 export leakage
- SEC-12 retention ve crash cleanup
- SEC-15 Lemmata operasyon izolasyonu

### Pinokyo Worked Example Kapısı

Şu riskler kapanmadan Pinokyo corpus'u public artifact veya makale kanıtı olarak kullanılmaz:

- RP-01, RP-02 ve RP-03 asset-level hak zinciri
- EPI-01 corpus metadata ve paratext
- EPI-02 duplicate ve edition ilişkileri
- EPI-06 OCR, edition ve normalization etkisi
- EPI-07 genre, audience ve chronology confounds

### Makale İddia Kapısı

Şu riskler kapanmadan güçlü reproducibility, stability veya validation dili kullanılmaz:

- EPI-03 unknown leakage
- EPI-04 segment bağımlılığı
- EPI-08 stability ve confidence ayrımı
- EPI-09 calibration contamination
- RP-05 environment determinism
- RP-06 reproducibility level
- RP-08 release metadata tutarlılığı

## 9. Olay Müdahalesi ve Fail-Closed Davranış

1. Şüpheli upload analiz edilmez; kullanıcıya içerik göstermeyen hata kodu verilir.
2. Timeout, OOM, worker schema hatası veya cleanup hatasında sonuç başarı gibi export edilmez.
3. Cross-session veya metin sızıntısı şüphesinde public servis kapatılır, temp storage korunmadan önce veri minimizasyonu ve hukuki gereklilik birlikte değerlendirilir.
4. Hak belirsizliğinde varlık public release'den çıkarılır; analiz için kullanılması ayrıca gerekçelendirilir.
5. Epistemik kapı ihlalinde sonuç silinmek zorunda değildir, fakat `invalidated` işareti alır ve claim evidence olarak kullanılamaz.
6. Her olay ticket, etkilenen run, düzeltme, tekrar test ve claim etkisiyle kaydedilir.

## 10. Kanıt ve Güncelleme Kuralı

- Her riskin durumu `planned`, `implemented`, `verified`, `accepted` veya `reopened` olarak izlenir.
- `verified` yalnız gerçek komut, fixture, tarih, yazılım sürümü ve saklanan artifact ile verilir.
- Bir kontrol değiştiğinde ilgili threat ID, ticket ve claim-evidence satırı birlikte güncellenir.
- Yeni upload türü, yeni export içeriği, yeni deployment biçimi, runtime AI veya kullanıcı hesabı eklenirse tehdit modeli yeniden açılır.
- P014 sonunda public-beta kapısı, P015 sonunda makale ve release kapıları bağımsız denetlenir.
