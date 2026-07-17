# Delta Agent Start Card

**Amaç:** Her yeni Codex veya Claude oturumunda minimum bağlamla doğru ticket'a başlamak.  
**Kanonik kaynak değildir:** Çelişkide `DEVELOPMENT_CONTRACT.md` ve kabul edilmiş ADR'ler geçerlidir.  
**2026-07-17 visual checkpoint:** Oğuz'un seçtiği Claude A5.1 tasarım sistemi
`codex/p014-visual-phase-b` dalında gerçek Streamlit yüzeyine aktarıldı. İlk
kanıtlı uygulama `3a554e0e76522672efaf547b1d03e12cb4f3531b`; draft PR #8'dir.
Sonraki tarayıcı-harness düzeltmeleri `15ce5dd532c5054191518ea292f5cb966338d068`
ve A5.1 bulgu kapatma commit'i `816dba94eb64458a1fe42bf4ad7b76e63d04a8d4`
üzerinden ilerledi. Bilimsel-yöntem, erişilebilirlik ve FAIR denetimleri nihai GO
değil, yeni düzeltme bulguları verdi. Bu bulgular çalışma ağacında giderildi;
failed-job cleanup, purpose-conditioned exploratory language, pre-run method
disclosure, warning semantics, accessible uploader naming ve A5.1 kaynak
paketinin Git içinde saklanması exact-commit yeniden denetimini bekliyor.
P014 tek `in-progress` ticket'tır. P007-P009 doğrulanmış minimum-alpha
dilimlerini koruyarak ertelenmiş tam-kapsam ve owner kapıları nedeniyle
`blocked` durumundadır. Tam P014 hâlâ P012'ye bağlıdır. Merge, image
publication, VPS, Caddy, DNS ve public activation için Oğuz'un ayrıca açık kararı
gerekir. Önce `docs/development/phase-b-visual-integration.md`, sonra
`SESSION_HANDOFF.md` okunur.
**Güncel operasyonel iş:** Düzeltmeleri tek exact commit'te dondur; full verify,
bağımsız exact-SHA bilimsel/erişilebilirlik/FAIR yeniden denetimi ve canonical
Linux CI çalıştır. CI tarayıcı JSON'u ile SHA-256 özetini Git kanıtına bağlamadan
review closure veya GO iddiası yazma.
**Aşağıdaki uzun aşama özeti tarihsel P014 gelişimini korur:** P001-P006 tamamlandı. P007 teknik kapılardan geçti; yalnız
Oğuz'un bütünleşik son uyarı dili ve prepared-state browser kabulü açıktır.
P008'in dört hücreli Guided minimum-alpha akışı `7e9a28e`, P009'un sonuç ve yorum
sınırı yüzeyi `c5e39b0` exact commit'lerinde gerçek upload-to-R/stylo-to-result
Linux browser, remote clean-clone ve canonical CI kapılarından geçti. P009 kanıt
kaydı `RUN-20260715-0003`; kanıt-link commit'i `567d154` ve CI `29404000108`
yeşildir. P008 tam üç amaç ve ilgili known/unknown matris, P009 ise dendrogram,
Style Over Time tarih haritası ve geniş glossary için ertelenmiş `blocked` kalır;
Research Mode kilitlidir. Minimum P014 deployment paketi exact commit
`7f26dbe`, `RUN-20260715-0004` ve canonical CI `29420509541` ile Linux source,
gerçek R/stylo browser, hardened container stack, TLS/WebSocket, hostile-request,
runtime-inspection, denied-egress ve cleanup kapılarından geçti. Güncel ticket'ta
P014-AC-01 ile P014-AC-04 ve P014-AC-06 ile P014-AC-07 passed; Phase B yaşam
döngüsü yeniden doğrulanana kadar P014-AC-05, ayrıca P014-AC-08 ile P014-AC-10
pending'dir.
Kanıt-link commit'i `dea9e67` ve PR CI `29424064991` yeşildir. İlk read-only VPS
preflight'i `RUN-20260715-0005` olarak saklandı: Lemmata sağlıklı, `8502` boş,
fakat hostta desteklenen container runtime yoktur; yaklaşık 4 GiB RAM, sıfır swap
ve sınırsız mevcut Lemmata profili nedeniyle kurulumdan önce capacity kararı da
gereklidir. Kapı exit `21` ile canlı değişiklik yapmadan durdu. Registry image
publication artık tamamlandı: PR #4 normal merge ile `8579e4e` olarak `main`e
alındı, main CI `29426588836` geçti ve `RUN-20260715-0006` exact source image'ını
private GHCR'da immutable manifest
`sha256:596591039de86c39c976f984b5b22fc3fc040bd56a08c471cbb349aa6c84b4a2`
olarak bağladı. Kanıt PR #5 ile normal merge commit `cc44132` üzerinden `main`e
alındı ve main CI `29429031944` yeşil geçti. `RUN-20260715-0007` ikinci read-only
gözlemde cgroup v2 controller'larını, boş firewall baseline'ını, sıfır Lemmata
restart'ını ve sıfır memory pressure'ı doğruladı. Oğuz
`HD-20260715-0002` ile ADR-0018'in mevcut VPS + official Docker + yeni swap
oluşturmama yolunu yalnız ordered host preparation ve measurement için kabul
etti. İlk adversarial pre-execution review çelişkili faz sırası, runtime-absent
preflight, kesin olmayan Docker/release komutları, ilk-release rollback ve ayrı
pre-Caddy owner gate açıklarını buldu. `codex/p014-live-host-acceptance` dalında
deterministic content-free host gate, official-Docker installer, Docker-only
rollback, duration-based coexistence gate ve sıralı runbook uygulanıyor. Hedefli
109 test, Ruff, Docker shell syntax ve diff-check kapılarından geçti. Sonraki
browser-harness düzeltmesiyle ilgili paket 121 testten geçti. Yeni full local
verify 1.656 pass, bir canonical Linux skip ve yüzde 100 measured coverage
ile yeşildir. Son adversarial bulgular; schema `1.3.0` pre-mutation/origin/key,
erken first-release cleanup, partial Docker install rollback, immutable image
revision ve gerçek R/`stylo` handoff'unu bütün ölçüm süresi boyunca yineleyen
closed load gate ile kapatıldı. Bütçe sınırına takılıp karar üretmeyen ajan
denemeleri approval sayılmadı. Oğuz'un seçtiği son Claude Code denetimi, normal
PR/main CI ve yeni exact-main image publication geçmeden VPS değiştirilmez. Draft
PR #7 düzeltme commit'i `11a440b` için push CI `29484009945` ve PR CI
`29484013488` verify/container işlerinde yeşildir; önceki iki Linux failure
değiştirilmeden kanıtta tutulur. Sonraki kanıt commit'i `5c1b083` için push CI
`29484671596` tamamen geçti; eş PR CI `29484673782` yalnız ikinci browser export
indirmesinde `Download.path: canceled` ile düştü. Kaynak/test ve container
kapıları geçti. Working tree, Streamlit'in bağlı ve iki kez kararlı-idle olduğunu
doğrulamadan indirmeye basmayan, tekrar deneyip gerçek hatayı gizlemeyen düzeltmeyi
içerir. Bu düzeltmenin `268c525` commit'inde PR CI `29486381721` tamamen geçti;
push CI `29486378477` ise sonuç seçicisini açarken eski zorla-tıkla/`fill` fallback
yolunda takıldı. `5d57f14` seçiciyi erişilebilir `combobox` ve `option` rolleriyle
normal kullanıcı gibi işletir; yalnız liste açılmazsa `ArrowDown` yardımı
kullanır. Bu exact head için push CI `29487643303` tamamen geçti. Paralel PR CI
`29487646240` container ve gerçek bilimsel sonuç akışını geçti, fakat browser
harness kapasite tablosunu dört satır oluşmadan okuduğu için iki hazırlık oracle'ı
false kaldı. Working tree artık dört satırı bekler, iki kararlı tablo snapshot'ı
ister ve gözlenen satırları kanıta yazar. Yedi helper, 159 ilgili test ve 1.658
testlik full local verify yüzde 100 measured coverage ile yeşildir; bu tarihsel
bekleme PR #7'nin `26947e1` normal merge commit'iyle tamamlandı. Caddy/DNS veya
public activation yetkisi verilmedi.
`HD-20260714-0002` ve ADR-0015 hedefi kabul eder; tarih hiçbir başarısız kapıyı
geçersiz kılmaz.

## 1. Her Oturumda Oku

1. Bu dosya.
2. `SESSION_HANDOFF.md`.
3. `docs/development/roadmap-P001-P015.md` içindeki aktif, yoksa sıradaki planlanan
   ticket bölümü.
4. Aktif veya sıradaki ticket'ın `Claim/tehdit bağlantısı` satırında geçen kayıtlar:
   - `docs/research/claim-evidence-matrix.md`
   - `docs/security/threat-model.md`
5. Ticket'ın etkilediği ADR ve kod/test dosyaları.

Şu durumlarda `DEVELOPMENT_CONTRACT.md` ve `PROJECT_MEMORY.md` tamamen okunur:

- Yeni mimari veya yöntem kararı
- Belgeler arası çelişki
- Claim, scope, Pinokyo, PhiloEditor, FAIR, privacy veya authorship değişikliği
- P000/P015 kapanışı veya release kararı
- `SESSION_HANDOFF.md` bunu açıkça isterse

`docs/archive/` aktif talimat değildir. Tarihsel gerekçe gerekmedikçe okunmaz.

## 2. Değişmez Ürün Sınırları

- Delta, `delta.lemmata.app` üzerinde çalışan scholar-led stilometri workbench'idir.
- Desteklenen akışlar, kullanıcının önce R/Python öğrenmesini veya kod yazmasını gerektirmez; bu yapısal başlangıç vaadi genel kolaylık veya kanıtlanmış öğrenilebilirlik iddiası değildir.
- v0.1 runtime AI, dış LLM API, login, analytics ve permanent project storage içermez.
- Ana hesaplama motoru R `stylo`; Python/Streamlit orchestration ve UI katmanıdır.
- UI v0.1'de yalnız İngilizcedir; string yapısı sonraki Türkçe/İtalyanca çeviriye hazırdır.
- Üç amaç vardır: Text Proximity, Group Comparison ve Style Over Time.
- Çıktı yalnız sonuç değil; corpus health, parameter sensitivity, interpretation limits ve FAIR-oriented run evidence içerir.
- Kesin authorship, confidence, pure style, causality veya universal usability dili yasaktır.

## 3. Scholarly Vibe Coding

- Oğuz, formal Python yazılım geliştirme uzmanlığı başlangıç koşulu olmadan Delta'yı Claude ve Codex ile geliştirir.
- Proje bu scholar-led, evidence-gated AI-assisted yöntemi `scholarly vibe coding` olarak adlandırır.
- Oğuz; araştırma sorusu, corpus, yöntem, haklar, acceptance, claim, yorum ve release kararlarının sahibidir.
- AI; kod, test, şema, dokümantasyon ve adversarial review üretir, fakat kendi çıktısını bilimsel olarak tek başına onaylayamaz.
- Human-decision ledger, PromptEvent, Ticket, Commit, ADR ve Run bağlantıları P001'den itibaren tutulur.
- Bu yaklaşım “AI programlama uzmanlığını gereksiz kılar” veya “her araştırmacı güvenilir yazılım üretebilir” iddiası değildir.
- Kanonik karar `decisions/ADR-0008-scholarly-vibe-coding.md` içindedir.

## 4. Yöntem Sınırları

- Guided Mode MFW: 100, 300, 500, 1000.
- Sabit anchor: 500 MFW, yüzde 0 culling, whole text, Classic Burrows Delta. “Best setting” değildir.
- Unknown; MFW, culling, mean, standard deviation, parameter selection ve threshold calibration'dan çıkarılır.
- Public Research Mode en çok 24 sürümlü/hashli `research-grid-v1` hücresi çalıştırır.
- Tam 192 hücre yalnız controlled publication batch'te çalışır.
- Birincil bağımsız birim work'tür; segmentler bağımsız n sayılmaz ve fold'lara ayrılamaz.
- Stability, confidence değildir. Etiket eşikleri calibration benchmark'ta belirlenip locked test ve Pinokyo öncesi dondurulur.
- Kalibrasyon başarısızsa yalnız raw stability components gösterilir.
- Style Over Time kronolojik ilişkiyi araştırır; yaşlanma, olgunlaşma veya neden açıklamaz.

## 5. Pinokyo ve PhiloEditor Sınırı

- Pinokyo, tool-first makalenin diachronic worked example'ıdır; makalenin ana araştırma nesnesi değildir.
- Demo: `Collodi Before and After Pinocchio: Is the Apparent Stylistic Shift Robust?`
- Pinokyo calibration veya benchmark verisi değildir.
- İlk ve son eser karşılaştırması tek başına yeterli değildir.
- PhiloEditor yerel sürüm/varyant karşılaştırır; Delta bağımsız eserlerin global stilometrik konumunu ve robustluğunu inceler.
- Diff, alignment, variant annotation, two-column edition ve critical edition özelliği eklenmez.

## 6. FAIR, Haklar ve Gizlilik

- “FAIR-certified” denmez; ürün `FAIR-oriented` olarak tanımlanır.
- Rights kararı corpus düzeyinde değil, her asset için ayrı tutulur.
- Upload/analysis izni, export izni ve public redistribution izni birbirinden ayrıdır.
- Varsayılan export raw text içermez.
- P005/P014 hedef politikası: başarılı job'da raw ve normalized metin export
  sonrası silinir; hatada en çok 15 dakika tutulur.
- P005/P014 hedef politikası: diskte export en çok 1 saat, content-free log
  en çok 7 gün tutulur. Bu süreler P003 tarafından doğrulanmış değildir.
- Delta ve Lemmata aynı VPS'i ancak container, identity, network, volume, env, port, secret ve kaynak sınırları testle ayrılırsa paylaşır.
- “Completely isolated” iddiası kurulmaz.

## 7. Makale ve Değerlendirme

Kanonik tez:

> No-code access is not methodologically sufficient. Delta shows how a scholar-led interface can make corpus confounds, parameter sensitivity, interpretive limits, and reproducibility first-class outputs of literary stylometry.

Bu tez araştırma yönüdür; güçlü `reproducible` dili CE-11 ve CE-12 geçmeden başlıkta veya release claim'inde kullanılmaz. Gerekirse `reproducibility-oriented` denir.

- Oğuz geliştirir, birinci ve sorumlu yazardır.
- Barış structured expert walkthrough ve acceptance test yapar; ikinci yazardır.
- Katılımcılı user study yoktur. Tek uzman testi genel usability/ease/teachability kanıtı değildir.
- Hakan ancak benchmark/statistical validation sorumluluğunu fiilen alırsa üçüncü yazar adayıdır.
- AI ajanları yazar değildir; geliştirme katkısı disclosure ve provenance ile açıklanır.
- Scholarly vibe coding ana ürün tezinin yerine geçmez; provenance yeterliyse ikincil development case, değilse disclosure ve sınırlılık notudur.
- Hedef Umanistica Digitale, planlanan gönderim Şubat 2027.

## 8. Kanıt Önce Kuralı

- Ürün veya makale claim'i, `docs/research/claim-evidence-matrix.md` kapısı geçmeden güçlü dille yayımlanmaz.
- Güvenlik kontrolü, gerçek test artifact'ı olmadan `verified` sayılmaz.
- Başarısız run ve grid hücreleri saklanır; güzel sonuç seçilerek diğerleri gizlenmez.
- PromptEvent, Ticket, HumanDecision, Commit, ADR ve Run ayrı kimliklerdir.
- Reconstructed prompt kaydı native veya exact diye sunulmaz.
- Her ticket sonunda test komutları, sonuçları, kanıt yolları ve güncel handoff yazılır.

## 9. Şu Anda Ne Yapılacak?

Güncel tek iş draft PR #8'in review sürecidir. Exact implementation
`3a554e0e76522672efaf547b1d03e12cb4f3531b`, canonical run
`RUN-20260717-0001` ve kanıt
`provenance/evidence/P014/phase-b-visual-integration-validation.md` üzerinden
incelenir. Claude Code A5.1 kaynak paketi, özgün manifesti ve repository-safe
türev manifesti `provenance/evidence/P014/phase-a51-design-source/` altında
kalıcıdır. Oğuz açıkça onaylamadan merge veya deployment yapılmaz.

P004 complete durumundadır. Domain/CSV, Guided TXT ve ZIP, fail-closed rights,
selectable Corpus Review, exact correction, hash-bound confirmation, exact-commit
clean-clone ve GitHub CI kapıları geçti. Kapanış `RUN-20260712-0005`,
`HD-20260712-0002` ve
`provenance/evidence/P004/automated-acceptance-rehearsal-ci.md` ile kayıtlıdır.
Final owner walkthrough P015 ürün-hazır kapısında ayrıca yapılacaktır; P004 kapanışı
Safari, VoiceOver, genel usability, bilimsel sonuç veya deployment iddiası değildir.

P005 kaydı `provenance/tickets/P005.json` içinde `complete` durumundadır. Final
implementation `RUN-20260713-0003` ile clean-clone ve browser katmanlarında;
Git-backed exact Linux package `RUN-20260713-0004` ile SBOM, audit, checksum ve
container katmanlarında geçti. Geçici write-capable capture workflow'u kaldırıldı.
Closure tree `029248b`, normal CI run `29269051028` içinde verify ve canonical
container işlerinde yeşildir. Tarihsel quota failures değiştirilmeden
`provenance/evidence/P005/final-ci-validation.md` içinde tutulur.

P006 kaydı `provenance/tickets/P006.json` içinde `complete` durumundadır. Accepted
ADR-0013 ve `HD-20260713-0002` yöntemi önceden dondurdu. Fixed worker ve handoff
commit'i `f0800c8`; retained worker source `79cb268`, capture `29340236382`,
evidence-only commit `7359cbe` ve `RUN-20260714-0004` zinciriyle doğrulandı.
Capture job kaldırıldı. Durable audit commit `d676d90`, Linux CI run `29350106890`
ve exact-commit remote clean-clone `RUN-20260714-0005` ile geçti. P006-AC-01 ile
P006-AC-08 fixture-local sınırda passed durumundadır.

P006 preprocessing, public Start analysis, production limitleri, secure erase veya
Delta-LDA host isolation iddiası kurmaz. Genel CE-04 P007'yi, tam CE-07 P010/P011'i
bekler. P007 implementation commit'i `b42da99`; `RUN-20260715-0001` ve
`provenance/evidence/P007/corpus-health-diagnostics-validation.md` deterministic
preparation, confound/overlap/feature-capacity projeksiyonu, content-free CSV,
clean-clone ve Linux CI kanıtını bağlar. P008 minimum Guided akışı exact commit
`7e9a28e`, `RUN-20260715-0002` ve CI `29388984019` ile doğrulandı: resolved config,
one-time P007 READY admission, P006 execution, locked Research Mode ve gerçek
browser akışı bağlıdır. P009 minimum sonuç yüzeyi exact commit `c5e39b0`,
`RUN-20260715-0003` ve CI `29402396790` ile doğrulandı: dört hücre durumu, sabit
500-MFW reading reference, distance heatmap, exact-tie nearest-neighbor tablosu,
deterministic MDS haritası, semantic table parity, claim lint ve raw-text-free
result export bağlıdır. Kanıt commit'i `567d154`, CI `29404000108` içinde yeniden
geçti. Tam P008 AC-09 ve tam P009 görsel genişletmeleri Public alpha'yı engellemez.
P014 minimum package exact implementation commit'i
`7f26dbe82437e7f9757e7c35b10b7666a3078578`, run kaydı
`RUN-20260715-0004` ve canonical CI `29420509541` ile doğrulandı. Kanıt:
`provenance/evidence/P014/canonical-alpha-stack-validation.md`. Kanıt-link commit'i
`dea9e67154d75852c5d69db9871fd4a1868bc236`, PR CI `29424064991` içinde yeniden
geçti. İlk target-host preflight'i `RUN-20260715-0005` ve
`provenance/evidence/P014/target-host-read-only-preflight.md` ile kayıtlıdır:
Lemmata 20/20 HTTP 200 ve 267,73 ms p95 ile sağlıklı, `8502` boş, fakat container
runtime yoktur. Host değiştirilmedi; AC-08 pending kaldı. PR #4 normal merge ile
`8579e4e335cfa3ccbd1368588bf11d60dca08764` olarak `main`e alındı ve main CI
`29426588836` geçti. `RUN-20260715-0006` ve
`provenance/evidence/P014/immutable-image-publication.md`, exact green image'ı
private GHCR'da immutable digest
`sha256:596591039de86c39c976f984b5b22fc3fc040bd56a08c471cbb349aa6c84b4a2`
ile bağlar; `latest` yayımlanmadı. Host hazırlık kararı ve PR #7'nin merge
edilmesi canlı kurulum yetkisi değildir. Delta-only kurulum, public TLS,
Lemmata coexistence/load, restart-cleanup, rollback ve owner walkthrough ayrı
bir gelecekteki karar dizisidir. Bu kapılar ve açık owner kararı olmadan DNS,
Caddy veya public activation yapılmaz.
