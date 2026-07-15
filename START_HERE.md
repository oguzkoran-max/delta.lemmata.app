# Delta Agent Start Card

**Amaç:** Her yeni Codex veya Claude oturumunda minimum bağlamla doğru ticket'a başlamak.  
**Kanonik kaynak değildir:** Çelişkide `DEVELOPMENT_CONTRACT.md` ve kabul edilmiş ADR'ler geçerlidir.  
**Güncel aşama:** P001-P006 tamamlandı. P007 Deterministic Preprocessing and
Corpus Health `codex/p007-preprocessing` dalında teknik olarak uygulanmış ve
exact-commit clean-clone/Linux CI kapılarından geçmiştir; yalnız Oğuz'un son
corpus-uyarı dili ve prepared-state browser kabulü açıktır. `HD-20260714-0001`
yöntem paketini kabul etti; ADR-0014 Accepted durumundadır. `HD-20260714-0002`
ve ADR-0015, gerekli P007, minimum P008/P009 ve minimum P014 kapıları geçerse
2026-07-17 için açıkça etiketli Public-alpha hedefini kabul eder; tarih hiçbir
başarısız kapıyı geçersiz kılmaz.

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
clean-clone ve Linux CI kanıtını bağlar. Sıradaki tek ana iş P008 için kapalı
parameter-review sözleşmesini kurmak ve Run eylemini yalnız one-time P007 READY
authority üzerinden mevcut P006 execution yoluna bağlamaktır. P007'nin son owner
uyarı dili kabulü ayrı ve açık kalır.
