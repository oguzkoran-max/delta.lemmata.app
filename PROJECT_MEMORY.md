# Delta Project Memory

**Son güncelleme:** 2026-07-14

**Durum:** P005 tamamlandı; P006 aktif, yöntem kararı kabul edildi ve kapalı
worker-sözleşmesi checkpoint'i exact Linux CI kapısından geçti

**Kod:** English-only workbench'te P004 guided corpus documentation ve P005 lifecycle
foundation var: ayrı session/job identity, payload-free SQLite queue, private
workspace, guardian-managed POSIX process control, durable terminal ACK,
execution-bound recovery receipt ve conservative lifecycle projection var. P006
input/result/fatal-error modelleri, strict parser, semantic validator, saf scientific
finalizer ve güvenli bounded workspace read eklendi; public analiz, R worker, parity
ve durable scientific-result entegrasyonu henüz yok

**P006 başlangıcı:** `codex/p006-stylo-worker` dalı ve
`provenance/tickets/P006.json` açıldı. Dört kullanılabilir read-only mercek ile
schema/provenance, FAIR/claim, yöntem ve security/lifecycle sınırları incelendi; iki
ilk deneme büyük parent wiki nedeniyle bütçede kaldı ve approval sayılmadı. P006
whole-text feature-count boundary kullanacak; preprocessing P007'de kalacak. Process
exit zero scientific success değildir; strict output ve semantic validation durable
terminal state ve guardian ACK'den önce gelir. stylo 0.7.71 kaynak incelemesi,
Wurzburg yolunun combined matrix'i yeniden scale edebildiğini gösterdi; known/unknown
Cosine Delta known-derived z-scores üzerinde `dist.cosine` kullanacaktır. Önerilen
CC0 fixture, C.UTF-8/UTC, seed 20260713, 1e-6 parity ve 1e-12 structural/tie
protokolü `HD-20260713-0002` ile kabul edildi.

**P006 sözleşme checkpoint'i:** Kapalı v1 wire profili en çok 20.000 özellik, 50
belge, 64 fit, 192 hücre ve 1.000 MFW kabul eder; 32 MiB input/result üst sınırları
en kötü durum kanonik JSON hesabıyla profile bağlanır. Known-only MFW sırası,
culling, yüzde relative frequency, sample standard deviation, complete/partial/
failed türetimi ve matris invariants doğrulanır. Unknown-only özellik ve sıfır
candidate-overlap geçerlidir fakat fitting'i etkileyemez. Üç bağımsız denetim;
aggregate-count, dev JSON integer, FIFO, çift JSON parse, culling sınırı, unknown
canary, denominator ve UTF-8 tie açıklarını buldu; tamamı kapatıldı. Aynı denetim,
erken guardian entegrasyonunun artifact kimliği ve crash recovery taşımadığını
gösterdiği için bu kod geri çıkarıldı. P006-AC-03 açık kalır; generic P005 ACK
bilimsel başarı kanıtı değildir. Son yerel kapı 1.073 test, 7.215 statement ve
1.898 branch ile ilk düzeltmeleri geçti; son bilimsel yeniden denetimde erişilebilir
Delta uzaklıklarını kesen keyfi `1e12` sınırı da kaldırıldı. Güncel doğrulama 1.075
test, 7.216 statement ve 1.898 branch ile yüzde 100 geçti. Exact implementation
commit `3c6ebe539b6c0a7f28c295cdcd74bc7e58135f6f`, GitHub Actions run
`29291282495` içinde verify, SBOM/dependency audit ve canonical Linux amd64
container kapılarından geçti.
P006-AC-01 ve P006-AC-05 bu dar kanıtla geçti; R worker, parity ve AC-03 açıktır.

**P005 ara durum:** Foundation ve retention zincirinden sonra guardian implementation
commit'i `3c746d1` üretildi. Separate guardian, leader ownership, SQLite-bound ACK,
execution-bound signed receipt ve gerçek app-loss yarışları uygulandı. 878 test ve
full measured statement/branch coverage geçti; `RUN-20260713-0001` exact-commit
clean-clone replay'i de geçti. Provenance-link commit `cfb503c`, GitHub CI run
`29215163561` içinde Linux verify, SBOM/dependency audit ve canonical amd64
container kapılarından geçti. P005 acceptance audit açıktır. Ayrıntı:
`provenance/evidence/P005/guardian-app-loss-validation.md`.

Bu dosya bağlam sıkıştırması, ajan değişimi ve Claude/Codex geçişlerinde kaybolmaması gereken uzun ömürlü proje hafızasıdır. Tam sohbet dökümü değildir. Kararları, gerekçeleri, reddedilen yolları, kanıtları ve açık soruları tutar.

## Okuma Sırası

1. START_HERE.md
2. SESSION_HANDOFF.md
3. Aktif ticket'ın roadmap bölümü
4. Ticket'ın işaretlediği claim, threat ve ADR kayıtları
5. Mimari/yöntem/release kararında DEVELOPMENT_CONTRACT.md ve bu dosya
6. İlgili kod, test ve run kanıtları

## Proje Özeti

Delta, delta.lemmata.app alanında çalışacak no-code bir stilometri workbench'idir. Desteklenen akışlarda kullanıcının önceden R veya Python öğrenmesini ya da kod yazmasını gerektirmeden edebiyat ve DBB araştırmacılarının stilometrik deney kurmasını hedefler. Ürünün ayırt edici yönü analiz çalıştırmak değil, parametre duyarlılığını, corpus risklerini, yorum sınırlarını ve tekrar üretim izini kullanıcıya göstermektir.

Runtime'da AI kullanılmayacaktır. Claude ve Codex geliştirme ajanları olarak kullanılabilir. Proje her iki araç arasında taşınabilir olmalıdır.

Geliştirme süreci de aynı no-code eşiğini araştırır. Oğuz formal Python yazılım geliştirme uzmanlığı olmadan, bilimsel karar sahipliğini koruyarak Delta'yı Claude ve Codex ile geliştirmektedir. Bu scholar-led ve evidence-gated yöntem `scholarly vibe coding` olarak adlandırılır.

## Onaylanmış Kararlar

| Alan | Karar | Gerekçe |
|---|---|---|
| Ürün adı | Delta | Burrows's Delta ve fark/değişim fikriyle uyumlu |
| Alan adı | delta.lemmata.app | Lemmata ürün ailesi ve aynı VPS kullanımı |
| Kanonik çalışma yolu | `~/Developer/delta.lemmata_app` | Sanal ortam ve araç dosyalarını Google Drive eşitlemesinden çıkarmak |
| GitHub origin | Özel `https://github.com/oguzkoran-max/delta.lemmata.app` | İzlenen kaynak ve Git geçmişi için uzak yedek; public release değildir |
| Lemmata launch entegrasyonu | `Launch Stylometry` sonraki ayrı ticket | Canlı parent siteyi P002 kapsamına gizlice dahil etmemek ve bağımsız regression/rollback kapısı kurmak |
| P002 ikinci-model denetimi | Claude önce read-only denetler, sonra kanıtlı eksikleri ayrı branch'te düzeltir; Codex son denetçi | Tanı ile uygulamayı ayırmak, self-preferential bias'ı azaltmak ve kabul edilmiş baseline'ı korumak |
| Runtime AI | v0.1'de yok | Maliyet, gizlilik, telif ve determinism |
| Motor | R stylo | Alan standardı ve hesaplama parity olanağı |
| Arayüz | Python ve Streamlit | Hızlı geliştirme, Lemmata tecrübesi |
| v0.1 UI dili | Yalnız İngilizce | lda.lemmata.app tutarlılığı ve daha dar QA kapsamı |
| Giriş deneyimi | Stilometriyi tanımlayan tek öğretici yüzey + görünür gerçek Purpose/Upload akışı | Kod bilmeyen kullanıcıyı yönteme yönlendirirken aracı marketing landing page'e çevirmemek |
| Görsel aile | Lemmata koyu yeşili + LDA açık çalışma alanı + soft mint öğretici yüzeyler | delta.lemmata.app'i ürün ailesine bağlarken operasyonel okunabilirliği korumak |
| Sidebar | Start here rehberi; build/engine bilgisi collapsed Technical status | Geliştirici sınırını ilk mesaj yapmamak; kullanıcıya sıradaki gerçek işi göstermek |
| Parametre UI sırası | Önce corpus review; sonra Guided sweep veya bounded Research controls | Corpus kapasitesini kontrol etmek ve sonuç-sonrası cherry-picking riskini azaltmak |
| Yerelleştirme | Mimari hazır, Türkçe ve İtalyanca sonraki sürüm | Metinleri sonradan koddan ayırma maliyetini önlemek |
| Ana değer | Uncertainty, interpretation, reproducibility | Basit bir stylo wrapper olmamak |
| Hedef kullanıcı | Kod bilmeyen DBB/edebiyat araştırmacısı | Teknik eşiği kaldırırken yöntemsel kontrolü korumak |
| Guided MFW | 100/300/500/1000 | Tek parametreye bağlı sonucu önlemek |
| Ana metrik | Classic Burrows Delta | Kanonik ve öğretilebilir başlangıç |
| Analiz amaçları | Text Proximity, Group Comparison, Style Over Time | Genel tool kapsamı ve Collodi örneğinin yöntemsel temeli |
| Unknown | Feature calibration'dan daima çıkarılır | Leakage ve transductive yanlılığı önlemek |
| Public Research Mode | Job başına en fazla 24 sürümlü hücre | Ortak VPS kaynaklarını korurken duyarlılığı göstermek |
| Full Research Mode | En çok 192 hücre, kontrollü publication batch | Yayın validasyonunu public hizmet yükünden ayırmak |
| Stability dili | Parameter stability, confidence değil | Tekrarlanan sonuç doğruluk garantisi değildir |
| Stability eşiği | Benchmark calibration sonrası, locked test ve Pinokyo öncesi dondurulur | Keyfi 75/50 eşiklerinden kaçınmak |
| FAIR dili | FAIR-oriented reproducibility package | FAIR'i sertifika gibi sunmamak |
| Makale | Tool-first DBB makalesi | Pinokyo veya De Amicis araştırmasını merkeze almamak |
| Worked example | Collodi Before and After Pinocchio | Style Over Time, confound ve kararlılık akışını göstermek |
| PhiloEditor sınırı | Delta diff, alignment, varyant anotasyonu veya kritik edisyon yapmaz | Aynı aracı yeniden üretmemek |
| Demo hak politikası | Asset-level rights manifest ve default no raw text | Kamu malı eser ile dijital edisyon hakkını ayırmak |
| v0.1 değerlendirme | Oğuz geliştirir, Barış structured expert walkthrough ve acceptance test yapar | Katılımcılı çalışma olmadan belgeli alan uzmanı QA sağlamak |
| Usability iddiası | Genellenebilir kolaylık veya öğreticilik iddiası yok | Tek iş birlikçi testi kullanıcı çalışması değildir |
| Kısa ürün vaadi | Desteklenen akışlarda önceden R/Python öğrenmek veya kod yazmak gerekmez | Başlangıç teknik eşiğini kaldırmak; genel ease/usability iddiası kurmamak |
| Reproducible claim'i | CE-11 ve CE-12 geçene dek `reproducibility-oriented` | Başlığı ve ana iddiayı kanıttan önce kesinleştirmemek |
| Geliştirme yöntemi | Scholar-led, evidence-gated `scholarly vibe coding` | Formal Python uzmanlığı olmayan alan araştırmacısının bilimsel sahipliği koruyarak AI ile tool geliştirmesini şeffaflaştırmak |
| Scholarly vibe coding claim'i | İkincil refleksif yöntem katkısı | Tool-first odağı korumak ve genellenebilir “AI herkes için yazılım üretir” iddiasından kaçınmak |
| De Amicis | Ayrı, sonraki edebiyat merkezli uygulama | TÜBİTAK çıktısını tool makalesine yüklememek |
| Makale hedefi | Umanistica Digitale | Tool, İtalyan corpus'u ve DBB odağıyla güçlü uyum |
| Makale liderliği | Oğuz birinci ve sorumlu yazar; Barış ikinci yazar | Geliştirme ve expert validation sorumluluklarını açıklaştırmak |
| Hakan'ın rolü | Benchmark ve istatistiksel doğrulamayı fiilen üstlenirse üçüncü yazar adayı | Katkı olmadan otomatik yazarlıktan kaçınmak |
| Gönderim hedefi | Şubat 2027 | Geliştirme, doğrulama, release ve yazım için aşamalı takvim |
| Ajan mimarisi | Agent-nötr sözleşme ve ince adaptörler | Codex ve Claude arasında kayıpsız geçiş |
| Hafıza | Sürekli checkpoint, yalnız pre-compaction değil | Sıkıştırma önceden haber vermeyebilir |
| P005 CI kanıt kanalı | Exact Linux CI'nin sekiz dosyalı path-neutral paketi outer SHA-256 manifestiyle Git'e bağlanır; geçici write workflow'u yakalamadan sonra kaldırılır | Kota-bağımlı artifact servisini zorunlu kılmadan inspectable ve kalıcı FAIR-oriented kanıt sağlamak |

## P004 Beginner-First Entry Experience

2026-07-12 giriş revizyonu, ilk ekranda stilometriyi ölçülebilir dil kullanım
örüntülerinin corpus-relative karşılaştırılması olarak açıklar. Common-word recurrence
somut başlangıç örneğidir. Observe -> Compare -> Interpret haritası analiz sonucu
değil kavramsal akış olarak etiketlenir. Compare Texts, Compare Groups ve Trace Style
Over Time seçimlerinin Question, Why use it ve Do not conclude açıklamaları sürekli
görünür. Sahte dendrogram, cluster, heatmap veya distance sonucu yoktur.

Final fresh-process Playwright altı viewport, individual TXT ve two-member ZIP
regression, keyboard selection, no overflow, no payload echo, no egress ve clean
console kapılarında geçti. 320px tasarımında kelime parçalanması giderildi ve ilk
amaç düğmesi görünür alana alındı. Full yöntem ve başarısızlık kaydı:
`provenance/evidence/P004/entry-experience-redesign-validation.md`. Bu değişiklik
general usability veya P004 acceptance iddiası değildir. Implementation commit
`b538807`, `RUN-20260712-0002` ile fresh no-hardlinks detached clone'da yeniden
kuruldu; 467 test, full measured coverage ve complete browser audit geçti.
Provenance-link commit `26a04e3`, GitHub CI run `29192912269` içinde verify,
SBOM/dependency audit ve Linux amd64 container işlerinde geçti.

2026-07-12 aile-paleti revizyonu, canlı `lemmata.app` ve `lda.lemmata.app`
görsellerinden koyu yeşil eylem, açık gri çalışma alanı/sidebar ve soft mint giriş
yüzeyini Delta'ya uyarladı. Sidebar artık teknik boundary yerine Start here ve
parametre sıralamasını anlatır; build ve engine bilgisi collapsed Technical status
içindedir. Ana akış Guided 100/300/500/1000 MFW taramasını, sabit 500 MFW + yüzde
0 culling + whole text + Classic Delta referansını ve gelecekteki bounded Research
Mode'u açıklar. Kontroller motor ve corpus-health kapılarından önce açılmaz. Kanıt:
`provenance/evidence/P004/family-palette-parameter-orientation-validation.md`.
Exact commit `54e479d`, `RUN-20260712-0003` ile fresh no-hardlinks detached
clone'da 468 test, yüzde 100 coverage ve aynı computed-palette browser audit'inden
geçti; clone temiz kaldı. Provenance-link commit `5d95ce4`, GitHub CI run
`29201459098` içinde verify, SBOM/dependency audit ve Linux amd64 container
işlerinde geçti. Bu kayıt P004 acceptance veya bilimsel analiz değildir.

## Ürün Tezi

> Stilometriyi kodsuz yapmak yeterli değildir. Kullanıcı, sonucun hangi corpus ve parametre kararlarına bağlı olduğunu, ne kadar kararlı olduğunu ve neyi kanıtlamadığını da görebilmelidir.

Delta sonuç üretme aracı değil, kanıt denetleme ortamı olarak konumlandırılacaktır.

## Makale Tezi

Makale Pinokyo hakkında yeni bir monografik yorum sunmayacaktır. Makale Delta'nın geliştirilmesi, epistemik tasarımı ve kanıtlı doğrulaması üzerinedir.

Kanonik tez:

> No-code access is not methodologically sufficient. Delta shows how a scholar-led interface can make corpus confounds, parameter sensitivity, interpretive limits, and reproducibility first-class outputs of literary stylometry.

**Kullanıcı onayı:** 2026-07-10. İngilizce-only v0.1 arayüzü ve bu makale tezi birlikte onaylandı.

Başka bir deyişle Delta'nın yeniliği yeni bir metrik icat etmek veya styloyu yalnız web'e taşımak değildir. Yenilik, kullanıcının verdiği her corpus ve parametre kararını görünür hale getiren, kırılgan sonuçları saklamayan ve her run için yeniden üretim kanıtı üreten bütünleşik bir araştırma protokolüdür.

İkincil yöntem katkısı, Delta'nın hangi geliştirme modeliyle üretildiğini sorar: formal Python yazılım geliştirme uzmanlığı olmayan bir edebiyat/DBB araştırmacısı, AI ajanlarını kullanırken yöntemsel sahipliği, auditability'yi ve bilimsel claim sorumluluğunu nasıl koruyabilir? Yanıt `scholarly vibe coding` protokolü, human-decision ledger ve P001 sonrası provenance coverage ile kanıtlanacaktır. Coverage yetersizse bu bölüm yalnız disclosure ve refleksif sınırlılık notu olarak kalır.

Pinokyo'nun rolü:

- Halka açık, hakları denetlenmiş Collodi demo corpus'unda pivot eser
- Yazar tespiti olmayan diachronic worked example
- Baştan sona kullanıcı akışının gösterimi
- Chronology-confound audit ve leave-one-work-out gösterimi
- FAIR-oriented paketin yeniden çalıştırılabilir örneği

Pinokyo bölümü makalenin yaklaşık %10-15'i olmalıdır.

## Pinokyo Demo Tasarımı

Ana soru:

> Seçili Collodi corpus'unda Pinokyo olası bir stilometrik dönüm noktası gibi görünüyor mu ve bu görünüm tür, hedef kitle, edisyon, tek-eser etkisi ve parametre değişikliklerinden sonra korunuyor mu?

İki katman:

- Audience-controlled core: Giannettino, Minuzzolo, Pinokyo ve hak denetimini geçen 1884-1890 çocuk/genç okur eserleri
- Broad career panorama: Un romanzo in vapore, I misteri di Firenze ve uygun diğer erken eserlerin eklendiği, açıkça exploratory kariyer görünümü

Yalnız ilk ve son eser karşılaştırılmaz. En az üç kronolojik nokta ve toplam altı bağımsız eser yoksa çıktı exploratory sayılır. Segmentler bağımsız eser sayılmaz. Pinokyo calibration veya benchmark verisi değildir.

PhiloEditor aynı eserin iki redaksiyonundaki yerel varyantları gösterir. Delta farklı yıllarda yayımlanan bağımsız eserlerin global stilometrik konumunu, corpus karışmalarını ve parametre kararlılığını inceler. İki Pinokyo sürümünün diff veya group comparison analizi v0.1 demosundan çıkarılmıştır.

Hak notu: PhiloEditor ve ATLAS CC BY 4.0 gösterse de 1983 Castellani Pollidori metni ayrı kullanım koşullarına sahiptir. Platform lisansı ham kritik metnin yeniden dağıtım izni sayılmaz.

Ayrıntılı protokol: docs/methodology/pinocchio-diachronic-worked-example.md

## Lemmata Denetiminden Çıkan Dersler

Lemmata sitesi, DSH proof'u, GitHub deposu ve prompt geçmişi incelendi. Beş bağımsız ajan editoryal, metodolojik, FAIR, mimari ve adversarial değerlendirme yaptı.

Taşınacak iyi uygulamalar:

- Açık kaynak kod ve sürümlü release
- DOI ve yazılım atfı
- Başarısız denemeleri saklama
- Alan uzmanı karar kontrolü
- Gerçek corpus ile doğrulama
- Açık AI disclosure
- Parametre ve environment export'u

Delta'da düzeltilecek noktalar:

- PromptEvent, Ticket, HumanDecision, Commit, ADR ve Run kimlikleri ayrı tutulacak
- Retrospektif kayıtlar exact veya native diye sunulmayacak
- Tam yanıt yayımlanmıyorsa "every prompt and response" denmeyecek
- Data Availability yalnız gerçekten depolanmış nesneleri sayacak
- Tek bir sürüm kaynağı CFF, app, package ve DOI metadata'sını üretecek
- Python ve R environment'ları tam kilitlenecek
- Determinism ile cross-version stability ayrı iddialar olacak
- Privacy dili gerçek retention davranışıyla aynı olacak
- Canlı link ve metadata drift'i CI ile denetlenecek

## Mevcut Briefte Çözülen Çelişkiler

Eski CLAUDE.md tarihsel arşive taşındı. Yeni sözleşme şu eski çelişkileri geçersiz kılar:

- Guided Mode 100/300/500 değil, 100/300/500/1000
- Stability yalnız 3/4 aynı kuralına dayanmaz
- Unknown'u feature calibration'dan çıkarmak isteğe bağlı değildir
- FAIR Package yerine FAIR-oriented reproducibility package
- Ham metin başarılı job sonrasında 24 saat tutulmaz
- De Amicis makalenin başrolü değildir
- Pinokyo tool-first makalenin worked example'ıdır
- Pinokyo known-answer unknown deneyi değil, diachronic Style Over Time örneğidir
- PhiloEditor sürüm karşılaştırması Delta demosunun parçası değildir
- Stability etiketi confidence anlamına gelmez ve keyfi 75/50 eşiği kullanmaz
- Tekrarlanan P011-P014 numaraları yeni tekil P001-P015 haritasıyla geçersizdir

## Ertelenen veya Reddedilen Yollar

- v0.1 runtime AI: ertelendi
- Kullanıcı hesabı ve kalıcı proje saklama: reddedildi
- PDF/DOCX/EPUB/TEI ingestion: v0.1 dışında
- Kesin yazar tespiti dili: reddedildi
- Delta'yı ilk web stilometri aracı diye sunmak: reddedildi
- SVC'yi ikinci kez makalenin ana katkısı yapmak: reddedildi
- De Amicis coğrafya etkisini nedensel iddia olarak sunmak: reddedildi
- Pinokyo'yu ana edebiyat araştırması yapmak: reddedildi
- Tam konuşma transkriptlerini her checkpoint'e kopyalamak: reddedildi

## P002 Kapanış

P002, 2026-07-10 tarihinde English-only Streamlit workbench shell olarak kapandı.
İlk ekran doğrudan araştırma iş istasyonudur; Text Proximity, Group Comparison ve
Style Over Time amaçları ile Guided/Research ayrımını gösterir. Secure ingestion
ve scientific computation gerektiren kontroller disabled ve kapsam sınırı açık
olarak sunulur.

P002'nin kanıtı:

- Merkezi English registry: 90 user-facing string, language selector yok
- Ortak interface state sözleşmesi: empty, loading, error, cancelled, complete
- Desktop 1440x1000 ve mobile 390x844 browser kanıtı
- Keyboard purpose-selection testi ve sıfır unnamed visible control
- Egress-denied shell smoke testi; gözlenen external AI/analytics request sıfır
- 40 test, strict mypy, yüzde 100 ölçülen Python source coverage
- `a888e7c81e5fdae12687903de29d0728f5c7cbd5` clean-clone rerun sonucu: pass
- Sekiz ara hata/düzeltme P002 acceptance raporunda saklandı

Bu kapanış secure upload, gerçek `stylo` çalışması, genel usability, production
security veya bilimsel geçerlilik kanıtı değildir. `Launch Stylometry` parent-site
entegrasyonu da P002 dışında bırakılmıştır.

## Açık Kanıt İşleri

P002; Claude bağımsız denetimi, Codex düzeltmeleri, karşıt yeniden denetim ve canlı
ürün kapısından sonra `8ef2582` merge commit'iyle main'e alındı. Açık P0/P1/P2 yoktur.

P003 Secure Ingestion `codex/p003-secure-ingestion` branch'inde uygulanmış ve
2026-07-11 tarihinde tamamlanmıştır. Katı TXT/CSV/ZIP parser, versioned limits,
deterministic fuzz, rejected-widget cleanup, browser audit, exact-commit clean
clone ve `RUN-20260711-0003` otomatik paketi geçti. Oğuz iki TXT + valid CSV,
strict ZIP ve unsafe CSV rejection-and-clearing akışlarını elle çalıştırdı;
`RUN-20260711-0004` ve nihai `HD-20260711-0008` ile kabul verdi. İlk kısa devam
yanıtı ve bağımsız belirsizlik bulgusu `HD-20260711-0007` içinde ayrı tutulur. TXT, ZIP ve metadata
CSV dışındaki formatlar ile metadata anlamı, retention garantileri ve scientific
computation bu ticket'ın dışındadır.

İnsan kabulü ve kapanış kayıtlarını içeren `d99aa7158caa8ba78ac8b2c1810eb61d9d21b8a2`
commit'i temiz çalışma ağacında `RUN-20260711-0005` ile yeniden doğrulandı. 232 test,
yüzde 100 statement/branch coverage ve bütün repository, supply-chain ve R-lock
kapıları geçti.

Repository çalışma kopyası 11 Temmuz 2026'da Google Drive'dan
`~/Developer/delta.lemmata_app` yoluna taşınmış ve özel GitHub origin'i
eklenmiştir. Bu operasyon P003'ün implementation veya acceptance sonucunu
değiştirmez. Karar ve doğrulama kapıları ADR-0010'da kayıtlıdır.

GitHub CI'nin varsayılan tek-commit checkout'u tarihsel provenance commit'lerini
çözemediği için verify işi tekrar tekrar başarısız görünüyordu. `f7a75b0` hotfix'i
verify checkout'una `fetch-depth: 0` ekledi; `0b0b349` ile main'e alındı.
GitHub run `29167750356` ve main run `29167865311` verify, SBOM/audit ve container
işlerinde geçti. Ayrıntı `provenance/evidence/P004/ci-shallow-history-failure.md`.

Sonraki ticket acceptance kapılarında izlenecekler:

- Aday Collodi eserlerinin item-level source, edition ve rights audit'i
- `research-grid-v1` içindeki kesin 24 hücrenin benchmark öncesi dondurulması
- Token, segment, CPU, RAM ve timeout sınırlarının yük testiyle sayısallaştırılması
- Stability eşiklerinin calibration benchmark üzerinde belirlenmesi

## Sonraki Adımlar

P004 versioned domain models, controlled vocabularies, generated JSON schemas,
purpose-aware cross-field validation, canonical inventory hash, semantic metadata
invalidation ve 58-column CSV round trip 2026-07-12 yerel adayında uygulanmıştır.
Ayrı rights-source kayıtları korunur; statement-only beyan public redistribution
kapısını açamaz. Aday `8dd85c1` commitinde 390 test ve %100 statement/branch
coverage ile geçmiştir; `RUN-20260711-0006` exact-commit yerel kanıtıdır. GitHub CI
`29172847800` verify, SBOM/audit ve Linux container işlerinde geçmiştir.

Guided individual-TXT Upload -> Describe -> Review akışı 2026-07-12 adayında
uygulanmıştır. Payload-free catalog, deterministic rights questionnaire, semantic
timeline, Rights Action Matrix, readiness counters ve üç documentation download
fresh-process Playwright ile altı viewport'ta; tam kaynak ağacı 418 test ve yüzde 100
statement/branch coverage ile geçmiştir. P004 acceptance verilmemiştir.

Hash-bound Review projection aynı gün uygulanmıştır. Genre, audience, adaptation,
collection ve acquisition source type için composition bars; identity, chronology,
edition, source, classification, rights ve normalization için Metadata Completeness
Matrix tek immutable projection'dan semantic table ve iki P003-validated CSV üretir.
Rights completeness permission anlamına gelmez; aggregate quality score yoktur.
Fresh-process Playwright visual/table/CSV key parity, work x 7 matrix shape, üç
focusable table region, beş download, altı responsive Review viewport, no external
host ve no payload echo kapılarını geçti. İlk focus failure ile manuel incelemede
reddedilen clipped-count screenshot korunmuştur. Tam aday 457 test ve 2.984 statement
ile 830 branch'in yüzde 100'ünde geçti; P004 acceptance verilmemiştir.

Selectable timeline, correction routing ve final documentation confirmation aynı
gün tamamlandı. Timeline projection/table row key parity taşır; guided correction
exact work ve section'a döner; CSV correction tutulmayan source CSV'yi taklit etmez,
exact `work_id` ve field adını verir. Guided metadata payload-free state ile korunur.
Final mapping/rights acknowledgement inventory hash'ine bağlıdır, blocker varsa
disabled ve rebuild ile invalidated olur. Mobil custom header örtüşmesi manuel
görüntü denetiminde bulunup düzeltildi. Final aday 464 test, 3.132 statement ve 868
branch'in yüzde 100'ünde; fresh-process Playwright altı viewport, keyboard
confirmation, dört focusable data region, beş download, no overflow, no egress ve
no payload echo kapılarında geçti. P004 acceptance verilmemiştir.

Guided ZIP member catalog aynı gün tamamlandı. P003 parser'ın zaten hesapladığı safe
member label, SHA-256, byte, line, token ve limit-profile özeti immutable,
payload-free receipt olarak açılır; parser veya limitler değişmez, ZIP yeniden parse
ya da extract edilmez. Individual TXT ve ZIP member aynı deterministic P004
catalog'una girer. Upload member catalog'u görünür; iki member iki guided form ve iki
Review work satırı üretir. Browser payload, archive asset ID, storage name ve archive
SHA P004 state'ine taşınmaz. Nested safe member path metadata CSV template'ten geçer.
Final aday 467 test, 3.165 statement ve 878 branch'in yüzde 100'ünde; fresh-process
Playwright individual-TXT regression + two-member ZIP, mobile no-overflow, visible
unknown-rights blocker, no payload echo, no egress ve clean console kapılarında
geçti. P004 acceptance verilmemiştir.

Birleşik Guided UI implementation commit'i `c82740d` aynı gün yeni bir
`--no-hardlinks` detached klonda committed Python/R lockfile'larından bootstrap
edildi. `./scripts/verify.sh` 467 test, 3.165 statement, 878 branch ve yüzde 100
coverage ile; fresh-process browser audit individual-TXT regression ve two-member
ZIP akışında geçti. Klon testlerden sonra temiz kaldı. Exact-commit kayıtları
`RUN-20260712-0001` ve
`provenance/evidence/P004/guided-ui-exact-commit/report.md` içindedir.
Provenance-link commit'i `4c3bb8a` GitHub CI run `29190917436` üzerinde verify,
SBOM/audit ve canonical Linux amd64 container işlerinde geçti.

1. Oğuz terminology/negative-rights/correction/timeline/confirmation/ZIP, Safari ve VoiceOver walkthrough'unu tamamlasın.
2. Kabul veya ret kararını HumanDecision olarak kaydet; yalnız kabulde P004'ü kapat.
3. LiberLiber pilot manifestini araştırma verisi değil, hakları izlenebilir test girdisi olarak değerlendir.

## Anahtar Kullanıcı İfadeleri

> "Burada daha çok Pinokyo araştırmasından ziyade biz bir tool geliştiriyoruz."

> "Bakın bu tool çalışıyor demek önemli; en azından bu toolu denediğimiz örnek de Pinokyo diyebilmek."

> "PhiloEditor mutlaka ama mutlaka farklı olmalı. Farkı ortaya koymalıyız."

> "Tamam beğendim, unutma devam edelim."

> "Katılımcılar olmayacak, ben geliştireceğim, Barış test edecek."

> "Python öğrenmeden de var; ben de tam olarak bilmiyorum, kendi önerdiğimiz scholarly vibe coding ile geliştiriyoruz."

> "Devam edelim."

> "Her bağlam penceresi daraldığında konuşmayı sıkıştıracaksın ama konuşmalarımızdan bir şey unutmanı istemiyorum."

> "FAIR ilkelerini unutma, her şeyi yaptığımız aşamalar şeffaf olmalı."

> "Launch Stylometry gibi bir şey düşünürüz ama o sonraki aşama."

> "tamam devam edelim"

## Hafıza Güncelleme Kuralı

Her onaylanmış karar bu dosyaya hemen eklenir. Oturum sonuna veya bağlam sıkıştırması uyarısına kadar beklenmez. Durum ve sıradaki tek iş SESSION_HANDOFF.md içinde güncellenir. Kritik dönüm noktası oluşursa memory/checkpoints/ altında tarihli özet açılır.

## P004 Exact Palette ve Language Weave (2026-07-12)

- `lemmata.app` ve `lda.lemmata.app` renkleri ekran görüntüsünden tahmin edilmedi;
  live CSS custom properties ve computed styles içinden birebir çıkarıldı.
- Ana Lemmata tokenları `#0f6e56`, `#0a5443`, `#e8f5f0`, `#c5e8dc`,
  `#5dcaa5`, `#f8faf9`, `#1a1a1a`, `#5c5c5c`, `#e2e5e4` ve exact
  coral/amber/blue/purple accent çiftleridir. LDA canvas/sidebar/control değerleri
  `#f8f9fa`, `#f0f2f6`, `#31333f` olarak korunur.
- Girişte Language Weave iki illustrative text row ile common words, punctuation,
  sentence rhythm ve vocabulary sinyallerini açıklar; sayı, axis, cluster,
  distance veya authorship sonucu üretmez.
- Attempt 1-5 fail JSON olarak, attempt 6 tam screenshot setiyle pass olarak
  saklandı. Full gate 468 test ve yüzde 100 statement/branch coverage ile geçti.
- Exact commit `374e2d0`, `RUN-20260712-0004` içinde fresh no-hardlinks clone'da
  aynı full gate ve browser audit'i geçti; clone temiz kaldı.
- Provenance-link commit `9864db4`, GitHub CI run `29204391922` içinde Linux
  verify, SBOM/dependency audit ve canonical amd64 container işlerinde geçti.
- Ajan raporları 10k bütçeyi aştığı için independent approval değildir.
- Bu checkpointte P004 revised human walkthrough için in-progress idi. Sonraki
  `HD-20260712-0002`, exact-commit ve CI kanıtı P004'ü teknik olarak kapattı; final
  product-ready owner walkthrough P015'e taşındı.

## P004 Otomatik Kabul Provası Kararı (2026-07-12)

- Oğuz, ara testleri Codex'in yürütmesini ve ortak insan walkthrough'unun ürün
  hazır olduğunda yapılmasını istedi: `HD-20260712-0002`.
- Bu karar otomasyonu insan kabulü gibi göstermiyor. Safari, VoiceOver, genel
  kullanılabilirlik, bilimsel geçerlilik ve release kabulü final walkthrough'a
  veya sonraki ticket kanıtlarına aittir.
- Browser harness fail-closed rights correction turuyla genişletildi:
  `permission_required` blocker üretir, exact `rights_status` correction guided
  değerleri korur, `analysis_only` upload/analysis iznini açarken export ve public
  redistribution'ı kapalı tutar.
- On bir başarısız harness/oracle iterasyonu açıkça raporlandı. On ikinci koşum
  altı viewport, Guided TXT, rights correction, beş download, confirmation ve ZIP
  akışlarının tamamında; no egress, no payload echo ve clean console ile geçti.
- Working-tree full gate 468 test, 3.174 statement, 880 branch ve yüzde 100
  coverage ile geçti.
- Implementation commit `9f3124a`, fresh no-hardlinks detached clone'da committed
  Python/R lockfile'larından yeniden kuruldu. `RUN-20260712-0005` içinde 468 test,
  3.174 statement, 880 branch, yüzde 100 coverage ve expanded browser audit geçti;
  clone temiz kaldı.
- Exact report, browser JSON ve checksum manifesti
  `provenance/evidence/P004/automated-acceptance-rehearsal-exact-commit/` altında
  bağlıdır.
- Provenance-link commit `c8ae4c2`, GitHub CI run `29207801898` içinde verify,
  SBOM/dependency audit ve canonical Linux amd64 container işlerinde geçti.
- `HD-20260712-0002` uyarınca yedi P004 acceptance ölçütü teknik kanıtla geçti ve
  Ticket complete oldu. Bu kapanış Safari, VoiceOver, genel kullanılabilirlik,
  bilimsel `stylo`, deployment veya final ürün kabulü değildir; ortak owner
  walkthrough P015'te yapılacaktır.
- Sıradaki tek iş P005 lifecycle, session isolation, bounded queue, cancellation,
  crash/restart cleanup ve retention modelidir.

## P005 Job Lifecycle Baseline (2026-07-12)

- P004 merge commit `d13e63c`, main CI `29208223198` üzerinde verify,
  SBOM/dependency audit ve Linux amd64 container kapılarından geçti.
- P005 branch `codex/p005-job-lifecycle`, Ticket
  `provenance/tickets/P005.json`, brief `prompts/P005-start.md`.
- Dört read-only ajan security, lifecycle/retention, accessible UX ve FAIR/claim
  sınırlarını bağımsız inceledi. Ortak P0 bulguları
  `provenance/evidence/P005/architecture-audit.md` içinde birleştirildi.
- Job ID ownership değildir. Server-generated session capability ayrı tutulur ve
  SQLite control store yalnız keyed owner digest ile content-free state saklar.
- Execution outcome, cancel request ve artifact cleanup orthogonal state'tir.
  Cleanup terminal sonucu silmez; illegal veya yarışan ikinci terminal outcome
  compare-and-swap ile reddedilir.
- P005 bir session-owned staged input API hazırlar: session başına bir, global dört,
  absolute bir saat TTL. P004 public UI payload-free kalır; bağlantı P008'de yapılır.
- Queue bir running ve en fazla üç queued job'dur. Queue/staging reddi job ID,
  workspace, process veya event ayırmaz. Queued deadline 15 dakikadır.
- Startup recovery yanında sürekli deadline-driven janitor gerekir. Success export
  ancak raw/normalized cleanup doğrulandıktan sonra görünür; failure/cancel/timeout/
  crash/abandon en geç 15 dakika, result/export bir saat, content-free events yedi
  gün içinde application-managed namespace'ten silinir.
- P005 sentetik finite-limit worker ile process control mekanizmasını doğrular.
  Gerçek R/stylo worker ve parity P006, production resource sayıları ve host
  isolation P014'tür.
- P005 kapanışı secure erase, swap/snapshot/backup, proxy buffer, CE-15 veya tam
  CE-14 production claim'i kuramaz. Final owner walkthrough P015'te kalır.

## P005 Retention ve Guardian Kararı (2026-07-13)

- `0e84b10` SQLite deletion ledger, schema migration, continuous janitor, exact
  deadline sınırları, success cleanup-before-publication, result/export expiry ve
  verified-absence tombstone purge katmanını tamamladı.
- Full local gate 795 test, 5.262 statement, 1.404 branch ve yüzde 100 coverage ile
  geçti. Kanıt `provenance/evidence/P005/retention-janitor-validation.md`.
- Running startup recovery yalnız dışarıdan doğrulanmış worker-stop kanıtıyla
  `abandoned` geçişi yapar. Kanıt yoksa row ve workspace korunur; başarı uydurulmaz.
- Bağımsız denetim, mevcut daemon monitorün app `SIGKILL` sonrasında worker grubunu
  geride bırakabildiğini buldu. PID/PGID persist edip restart'ta `killpg` çağırma
  yaklaşımı identifier reuse nedeniyle reddedildi.
- Kabul edilen sıradaki mimari yön: app-liveness pipe kullanan ayrı per-job guardian,
  PGID reuse penceresini kapatan owned group anchor, content-free authenticated
  recovery evidence ve gerçek macOS/Linux parent-loss testi.
- Guardian ayrıca unattended unsuccessful cleanup deadline'ını taşıyamazsa P005-AC-06
  açık kalır. Bu checkpoint production isolation, secure erase veya CE-14/CE-15
  doğrulaması değildir.

## P005 Git-Backed Linux Kanıt Kararı (2026-07-13)

- Final implementation commit `2a17ec6` için GitHub run `29220278021` dört denemede
  Linux verify, supply-chain generation ve canonical container katmanlarını geçti;
  yalnız hesap düzeyindeki `upload-artifact` kotası paketin tutulmasını reddetti.
- Job loglarını tek başına yeterli saymak ve belirsiz kota hesabını beklemek
  reddedildi. Oğuz `HD-20260713-0001` ile permanent Git-backed exact Linux evidence
  yolunu kabul etti.
- Paket tam sekiz non-empty UTF-8 dosya, JSON root validation, source checksum
  inventory, private path taraması ve sibling outer SHA-256 manifesti taşır.
- Capture yalnız disposable `codex/p005-evidence-capture` dalında write permission
  alır. Exact paket doğrulandıktan sonra workflow kaldırılacaktır.
- Bu karar P005'i kabul etmez, AC-08'i otomatik geçirmez ve scientific result,
  deployment, secure erase ya da production isolation iddiası kurmaz.

## P005 Kapanışı (2026-07-13)

- Path-neutral evidence source commit `d3ca0f6`, exact Ubuntu capture run
  `29268150070` ve normal CI run `29268150409` üzerinde 970 test, 6.551 statement,
  1.732 branch, yüzde 100 coverage, SBOM, audit ve canonical container kapılarını
  geçti.
- GitHub bot evidence commit `2eff470`, sekiz dosyalı paketi ve outer SHA-256
  manifestini kalıcılaştırdı. Detached replay bütün outer ve nested checksumları,
  JSON yapılarını, Python dependency graph'ını ve private-path absence kapısını
  doğruladı: `RUN-20260713-0004`.
- Geçici `contents: write` capture workflow'u kaldırıldı. Closure tree `029248b`,
  normal CI run `29269051028` içinde verify `86881820484` ve container
  `86881820512` ile geçti.
- P005-AC-01--AC-08 passed, Ticket complete ve blocker sıfırdır. Bu sonuç yalnız
  application-managed lifecycle, synthetic worker ve kayıtlı CI sınırındadır.
- Gerçek R/stylo computation ve parity P006; corpus health P007; public end-to-end
  workflow P008; production isolation, swap, snapshot, backup ve deployment P014;
  final owner walkthrough P015 kapsamındadır.
- Bu kapanışta sıradaki aday P006 olarak kaydedildi. P006 daha sonra ayrı Ticket,
  PromptEvent ve branch ile açıldı; üstteki güncel P006 başlangıç kaydı geçerlidir.
