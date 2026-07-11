# Delta Project Memory

**Son güncelleme:** 2026-07-11

**Durum:** P003 Secure Ingestion doğrulanarak `main`e alındı; P004 Metadata, Corpus Inventory, and Rights aktif

**Kod:** English-only workbench'te TXT/ZIP/CSV secure intake var; bilimsel hesaplama henüz yok

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

1. P004 versioned domain models, controlled vocabularies ve JSON schemas uygulanır.
2. Purpose-aware cross-field validation, stable error codes ve deterministic fixtures eklenir.
3. Canonical inventory hash ve semantic metadata invalidation contract uygulanır.
4. Form + CSV round trip, exact-confirmed mapping ve rights questionnaire bağlanır.
5. Upload, Describe, Review ile corpus-description görselleri uygulanır.
6. LiberLiber pilot manifesti araştırma verisi değil, hakları izlenebilir test girdisi olarak değerlendirilir.

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
