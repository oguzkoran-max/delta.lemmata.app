# Delta Development Contract

**Durum:** Kanonik; P001 acceptance kapısı geçti, P002 başlamaya hazır
**Onay tarihi:** 2026-07-10  
**Aşama:** P001 temel altyapı tamamlandı; kullanıcıya dönük iş akışı henüz başlamadı
**Alan adı:** delta.lemmata.app

Bu dosya Delta'nın ürün, yöntem, doğrulama, FAIR, güvenlik ve yayın sözleşmesidir. Claude, Codex veya başka bir ajan aynı sözleşmeye göre çalışır. Araç-özel talimatlar kanonik kararları değiştiremez.

## 1. Karar Hiyerarşisi

Çelişki halinde sıra şöyledir:

1. Kullanıcının tarih bakımından en yeni açık kararı
2. Bu DEVELOPMENT_CONTRACT.md
3. decisions/ altındaki kabul edilmiş ADR kayıtları
4. PROJECT_MEMORY.md
5. SESSION_HANDOFF.md
6. Kod, test ve release kanıtları
7. docs/archive/ altındaki tarihsel belgeler

Arşivdeki eski brief bağlam kaynağıdır, aktif talimat değildir.

## 2. Ürün Kimliği

**Ad:** Delta  
**Ürün ailesi:** Lemmata  
**Ürün türü:** Scholar-led, no-code, uncertainty-aware stylometry workbench  
**Hedef kullanıcı:** R, Python veya stylo bilmeyen edebiyat ve DBB araştırmacısı  
**Runtime AI:** v0.1'de yok  
**Ana motor:** R stylo  
**Orkestrasyon ve arayüz:** Python ve Streamlit  
**v0.1 arayüz dili:** Yalnız İngilizce; kod ve metin kataloğu sonraki Türkçe ve İtalyanca yerelleştirmeye hazır

Kısa ürün vaadi:

> Run supported stylometric workflows without first learning or writing R or Python code. Delta handles the code while keeping corpus choices, parameters, limitations, and rerun evidence visible.

Bu, desteklenen akışların ön koşul olarak R/Python kodlama bilgisi istemediği yönünde sınırlandırılmış bir tasarım vaadidir. “Herkes için kolay”, “hiç yöntem bilgisi gerekmez” veya “öğreticiliği kanıtlandı” anlamına gelmez.

Akademik konum:

> Delta is not a replacement for stylo. It is an interpretation, uncertainty, and reproducibility layer for literary stylometry.

## 3. Problem ve Yenilik

Delta yeni bir stilometri algoritması icat ettiğini iddia etmez. stylo, WebSty, JGAAP, Voyant ve öğretici kaynakların varlığını açıkça kabul eder.

Delta'nın katkısı altı noktadadır:

1. Teknik kurulumu kaldırırken yöntemsel kararları gizlememek
2. Tek dendrogram yerine parametre duyarlılığını göstermek
3. Corpus sağlığı ve yorum sınırlarını sonuçtan önce görünür kılmak
4. Style Over Time akışında kronoloji, tür, hedef kitle ve edisyon karışmasını denetlemek
5. Yanlış yazarlık ve nedensellik diline arayüz düzeyinde fren koymak
6. Her koşumu yeniden üretilebilir bir araştırma nesnesine dönüştürmek

Araç bir cevap makinesi değil, kanıt denetleme ortamıdır.

## 4. İzin Verilen ve Yasaklanan İddialar

İzin verilen dil:

- "X, yüklenen corpus ve seçilen ayarlar altında Y grubuna daha yakındır."
- "Bu yakınlık test edilen parametrelerin çoğunda korunmaktadır."
- "Sonuç parametre değişikliklerine duyarlıdır ve keşifsel yorumlanmalıdır."
- "İncelenen corpus içinde yayın tarihiyle ilişkili bir stilometrik örüntü görülmektedir."
- "Kronolojik örüntü, tür ve hedef kitle kısıtlandığında zayıflamaktadır."
- "Delta, doğrulanan fixture ve sürümler kapsamında stylo ile hesaplama eşliği göstermiştir."

Yasaklanan dil:

- "Delta yazarı kanıtlar veya kesin olarak bulur."
- "Bu metin kesinlikle Y tarafından yazılmıştır."
- "Ölçülen fark saf üsluptur ve konudan bağımsızdır."
- "Coğrafya, biyografi veya psikoloji üslup değişimine neden olmuştur."
- "Yazar yaşlandıkça üslubu olgunlaşmış veya sadeleşmiştir."
- "İlk ve son eser arasındaki fark, tek başına zamanın etkisini kanıtlar."
- "FAIR paketi araştırmanın kaliteli olduğunu garanti eder."
- "Araç herkes için kolaydır" veya "öğreticiliği kanıtlanmıştır", kullanıcı çalışması olmadan

## 5. v0.1 Kapsamı

v0.1'de bulunacaklar:

- Guided Mode
- Research Mode adıyla sınırlı uzman akışı
- Text Proximity, Group Comparison ve Style Over Time araştırma amaçları
- Yalnız İngilizce kullanıcı arayüzü
- .txt, .zip ve metadata .csv girdileri
- Corpus health check
- Classic Burrows Delta ana analizi
- Dendrogram, PCA veya MDS, distance matrix ve nearest-neighbor tablosu
- Parametre ve MFW kararlılık paneli
- Style Over Time için chronology-confound audit ve leave-one-work-out duyarlılık özeti
- What this shows ve What this does not show kartları
- FAIR-oriented reproducibility package
- Pinokyo public worked example
- No login, no analytics, no permanent project storage

v0.1 dışında kalanlar:

- Runtime AI veya dış LLM API'si
- PDF, DOCX, EPUB, OCR ve genel TEI ingestion
- Kullanıcı hesabı veya bulut proje kaydı
- Forensic-grade authorship attribution
- Open-set yazar tanıma motoru
- Otomatik edebî yorum
- Zenodo'ya tek tık yayın
- Genel amaçlı collation veya dijital edisyon platformu
- Aynı eserin sürümlerini hizalama, diff, varyant anotasyonu veya kritik edisyon üretimi
- Türkçe ve İtalyanca arayüz yerelleştirmesi

## 6. Kanonik Metodoloji

### 6.1 Ön İşleme

- UTF-8 ve Unicode NFC
- Surface word forms
- Lowercase açık
- Noktalama kaldırma açık
- Sayı kaldırma açık
- Stopword removal kapalı
- Lemmatization kapalı
- custom_exclusions.txt, tokenları metinden silmez; yalnız feature aday listesinden çıkarır
- Paratext ve editoryal ek temizliği corpus genelinde aynı politikayla yapılır
- Orijinal ve temizlenmiş metinler için ayrı SHA-256 kaydı tutulur

### 6.2 Guided Mode

Guided Mode her zaman 100, 300, 500 ve 1000 MFW değerlerini dener.

1000 MFW mümkün değilse sistem değeri sessizce değiştirmez. Hücreyi not enough features olarak raporlar.

Guided Mode'un anchor koşumu:

- 500 MFW
- 0% culling
- whole text
- Classic Burrows Delta

Anchor, "en iyi" ayar değildir. Sonuca bakarak ayar seçilmesini önleyen sabit başlangıçtır.

### 6.3 Research Mode

Araştırma ve yayın validasyonunda değerlendirilecek aday grid:

| Eksen | Düzeyler |
|---|---|
| MFW | 100, 300, 500, 1000 |
| Culling | 0%, 50%, 70%, 100% |
| Segment | whole text, 2.000, 5.000, 10.000 token |
| Distance | Classic Delta, Eder's Delta, Cosine Delta |

Tam grid en çok 192 hücre üretir. Corpus veya kaynak sınırları nedeniyle kullanılamayan hücreler NA kalır.

Public v0.1 arayüzünde tek job en fazla 24 hücre çalıştırır. Public preset, sonuç görüldükten sonra elle seçilen 24 ayar değildir. Dengeli, sürümlenmiş ve hashlenmiş `research-grid-v1` tanımıdır. Tam 192 hücre yalnız kontrollü publication batch veya yönetici koşumunda çalıştırılır.

24 hücre tek başına güvenli kaynak sınırı sayılmaz. Dosya, toplam token, segment, CPU, RAM, timeout ve eşzamanlı job sınırları deployment öncesi yük testiyle belirlenir. Global sınır aynı anda bir çalışan ve en fazla üç bekleyen R job'dur.

Classic Burrows Delta ana sonuçtur. Eder's ve Cosine Delta duyarlılık kontrolüdür. Farklı distance ailelerinin ham uzaklıkları birbirine ortalanmaz.

### 6.4 Unknown ve Holdout

Unknown ve blind holdout metinleri şunların tamamından çıkarılır:

- MFW sıralaması
- Culling hesabı
- Corpus ortalaması ve standart sapma
- Parametre seçimi ve eşik kalibrasyonu

unknown_in_feature_calibration=false v0.1 için zorunludur.

Unknown olmayan all-known analizler analysis_scope=transductive_exploratory olarak etiketlenir ve predictive validation sayılmaz.

### 6.5 Segmentasyon

- Birincil bilimsel birim bağımsız eserdir.
- Aynı eserin segmentleri farklı validation fold'larına dağıtılamaz.
- Segment sayısı bağımsız örneklem büyüklüğü gibi sunulamaz.
- Rolling veya overlapping pencereler anlamlılık testi için bağımsız gözlem değildir.
- "5.000 kelime minimumdur" gibi evrensel bir iddia kurulmaz.

### 6.6 Kararlılık

Stable, Partially stable ve Unstable yalnız MFW koşularının kaçının aynı gruba düştüğüne göre verilmez.

En az şu bileşenler birlikte değerlendirilir:

- Modal nearest group
- Nearest-neighbor rank agreement
- Aile içinde normalize edilmiş top-two margin
- Cluster co-placement
- Geçerli feature sayısı
- Distance aileleri arası yön tutarlılığı

Nihai eşikler calibration benchmark üzerinde belirlenir ve locked test ile Pinokyo koşumu görülmeden önce sürümlü protokole kaydedilir. Arayüz "confidence" veya "yüksek güven" demez; yalnız "parameter stability" veya "parametre kararlılığı" der. Kararlılık skoru benchmark doğruluğuyla beklenen yönde ilişki göstermiyorsa Stable, Partially stable ve Unstable etiketleri yayımlanmaz; yalnız ham bileşenler gösterilir.

### 6.7 Style Over Time

Style Over Time, v0.1'de ayrı bir araştırma amacı ve Guided Mode şablonudur. Analiz bir yazarın farklı tarihlerde yayımlanmış bağımsız eserleri arasındaki stilometrik konum değişimini araştırır. Aynı eserin sürümlerini karşılaştırmaz.

Zorunlu metadata alanları:

- `work_id`
- `title`
- `author`
- `composition_date_start`
- `composition_date_end`
- `first_publication_date`
- `edition_date`
- `date_certainty`
- `genre`
- `audience`
- `adaptation_status`
- `collection_status`
- `source_id`
- `source_url`
- `rights_status`
- `normalization_profile`

Koruyucu koşullar:

- Yalnız ilk ve son eserle zaman etkisi iddiası kurulmaz.
- Birincil bilimsel birim bağımsız eserdir; segmentler eser ağırlığını yapay olarak büyütmez.
- Tarih grupları sonuçlara bakılmadan önce tanımlanır.
- Tür, hedef kitle, uyarlama, edisyon ve metin uzunluğu kronolojiyle karışıyorsa arayüz bunu blocker veya güçlü uyarı olarak gösterir.
- En az üç kronolojik nokta ve toplam altı bağımsız eser yoksa çıktı yalnız exploratory olarak etiketlenir.
- Bir dönem yalnız tek eserle temsil ediliyorsa dönem düzeyinde genelleme yapılmaz.
- Leave-one-work-out koşumları, görülen örüntünün tek bir esere bağımlı olup olmadığını gösterir.
- Work-level tarih permütasyonu Research Mode'da keşifsel negatif kontrol olarak kullanılabilir; segment düzeyinde permütasyon yapılmaz.

Temel çıktılar:

- Tarihe göre etiketlenmiş work-level MDS veya PCA haritası
- Eser düzeyinde distance matrix
- Parametre kararlılık paneli
- Leave-one-work-out etki tablosu
- Chronology-confound audit
- What this shows ve What this does not show kartları

Delta kronolojik ilişkiyi ölçebilir, fakat yaşlanma, olgunlaşma, psikoloji veya nedensel gelişim açıklaması üretmez.

## 7. Doğrulama Rejimi

"Ekranda çalışıyor" validasyon değildir. Yayın öncesinde beş teknik kanıt katmanı zorunludur. Altıncı kullanılabilirlik katmanı, "öğretici" veya "kolay" gibi ampirik iddialar kurulacaksa zorunlu olur.

### 7.1 Hesaplama Eşliği

micro_delta_gold doğrudan R stylo ve Delta üzerinden çalıştırılır.

Kabul ölçütleri:

- Feature list birebir aynı
- Distance matrix farkı en fazla 1e-6
- Nearest-neighbor sırası aynı
- Aynı preprocessing ve locale

Bu test hesaplama eşliğini gösterir, yöntemin edebî doğruluğunu göstermez.

### 7.2 Known-Author Benchmark

- Her aday yazar için birden fazla bağımsız eser
- Tür ve dönem bakımından olabildiğince dengeli corpus
- Eser düzeyinde grouped veya nested cross-validation
- Her fold içinde feature calibration yalnız training eserleriyle yeniden yapılır
- Macro accuracy, confusion matrix, true-author rank, margin ve parameter agreement raporlanır

### 7.3 Diachronic Benchmark

Style Over Time akışı Pinokyo ile doğrulanmaz. Hakları açık, birden fazla yazarı ve her yazar için farklı yıllarda yayımlanmış bağımsız eserleri içeren ayrı bir diachronic benchmark kullanılır.

Kabul ölçütleri:

- Split ve yeniden örnekleme eser düzeyinde yapılır.
- Tarih farkı ile stilometrik uzaklık ilişkisi yazarlar arasında değerlendirilir.
- Tür ve dönem karışması açıkça raporlanır.
- Kararlılık skorunun doğru veya önceden tanımlı benchmark sonuçlarıyla ilişkisi calibration ve locked test olarak ayrılır.
- Pinokyo sonuçları eşik seçmek, parametre seçmek veya benchmark başarı oranını yükseltmek için kullanılmaz.

### 7.4 Negative Control

Aday kümesinde bulunmayan, aynı dönem ve türe yakın eserler kullanılır. Token sırasını karıştırmak geçerli negative control değildir, çünkü MFW frekanslarını değiştirmez.

Classic Delta forced-choice olduğu için araç güçlü bir none of the above iddiası kurmaz. Bunun yerine open-set sınırlamasını açıkça gösterir.

### 7.5 Tekrar Üretim

- Kilitli Python bağımlılıkları ve hashler
- renv.lock
- Sabit R ve stylo sürümü
- OS veya container image digest
- Locale, Unicode normalizasyonu ve komut argümanları
- Temiz clone ve mümkünse ağsız restore
- Geliştirici olmayan biri tarafından clean-room rerun

### 7.6 Expert Walkthrough ve Acceptance Test

v0.1'de katılımcılı usability study yapılmaz. Oğuz Koran ürünü geliştirir; Barış Yücesan release candidate üzerinde önceden tanımlanmış görevlerle structured expert walkthrough ve acceptance test uygular.

Test en az şu görevleri kapsar:

- Demo veya hakları açık test corpus'unu yükleme
- Metadata ve corpus-health uyarılarını değerlendirme
- Doğru analiz amacını seçme
- Parameter stability ve confound sonuçlarını yorumlama
- FAIR-oriented paketi dışa aktarma ve yöntem dosyasını bulma
- Aynı manifest ile rerun talimatını izleme

Yardım ihtiyacı, kritik hata, yanlış yorum, eksik kontrol ve arayüz kusurları sürümlü bir defect log'a kaydedilir. Barış testte geliştirici değildir, fakat proje iş birlikçisi ve olası ortak yazar olduğu için değerlendirme bağımsız kullanıcı çalışması sayılmaz.

Makalede "easy to use", "usable by general researchers", "teachability demonstrated" veya benzeri genellenebilir usability iddiaları kurulmaz. İzin verilen ifade, ürünün structured domain-expert walkthrough ve predefined acceptance tasks ile değerlendirildiğidir. Barış'ın gözlemleri araştırma verisi olarak analiz edilecekse etik gereksinim ayrıca incelenir; yalnız iç QA kaydı olarak kullanılırsa insan katılımcı bulgusu gibi sunulmaz.

## 8. Pinokyo Worked Example

Pinokyo makalenin ana araştırma nesnesi değildir. Delta'nın Style Over Time akışını, yorum sınırlarını ve tekrar üretim paketini gösteren halka açık worked example'dır.

Demo adı:

> Collodi Before and After Pinocchio: Is the Apparent Stylistic Shift Robust?

Araştırma sorusu:

> Hakları denetlenmiş seçili Collodi corpus'unda eserlerin stilometrik konumları yayın kronolojisi boyunca nasıl değişir ve Pinokyo'nun olası bir dönüm noktası gibi görünmesi tür, hedef kitle, edisyon ve parametre denetimlerinden sonra korunur mu?

Bu soru "Collodi'nin üslubu neden değişti?" veya "Collodi yaşlandıkça nasıl yazdı?" sorularını cevaplamaz. Görülen örüntünün ölçüm ve corpus kararlarına ne kadar bağlı olduğunu gösterir.

İki analiz katmanı kullanılır:

1. Audience-controlled core: 1877-1890 arasında çocuk ve genç okura dönük bağımsız eserler. Bu katman da tür ve uyarlama bakımından kusursuz eşleşmiş sayılmaz.
2. Broad career panorama: 1856-1890 arasındaki erken yetişkin düzyazısı ile geç çocuk ve eğitim metinleri. Tür ve hedef kitle kronolojiyle karıştığı için açıkça exploratory etiketlenir.

Aday eserler, nihai corpus değildir. Her biri item-level rights ve edition-quality gate'i geçmelidir:

- Erken panorama: Un romanzo in vapore (1856), I misteri di Firenze (1857)
- Geçiş adayı: I ragazzi grandi (1873), uyarlama niteliği açıkça işaretlenerek
- Core başlangıcı: Giannettino (1877), Minuzzolo (1878)
- Pivot: Le avventure di Pinocchio (1881-1883 tefrika veya hakları açık tek bir tanık)
- Core sonrası: Il regalo del Capo d'Anno (1884), Storie allegre (1887), La lanterna magica di Giannettino (1890)

Ana analizden çıkarılanlar:

- I racconti delle fate, çeviri olduğu için
- Ağır editörlü posthumous derlemeler
- İlk yayın ve metinsel tanık tarihi doğrulanamayan derleme parçaları
- Yalnız modern editör müdahalesi bilinen, kaynak metni doğrulanamayan dosyalar

PhiloEditor sınırı kesindir:

- Delta iki Pinokyo sürümünü hizalamaz.
- Ekleme, silme veya varyant sınıflandırması yapmaz.
- Satır içi, interlinear veya iki sütunlu edisyon karşılaştırması sunmaz.
- Anotasyon veya kritik edisyon üretmez.
- PhiloEditor verisini Delta'nın zorunlu veri kaynağı yapmaz.

PhiloEditor aynı eserin farklı redaksiyonları arasındaki yerel varyantları gösterir. Delta bağımsız eserler arasındaki global stilometrik konumu, kronoloji karışmalarını ve parametre kararlılığını denetler. Makalede bu görev ayrımı açık bir related-tools tablosuyla gösterilir.

Worked example çıktıları:

- Work-level kronolojik harita ve distance matrix
- Pinokyo öncesi, Pinokyo ve sonrası konumların parametre kararlılığı
- Audience-controlled core ile broad panorama karşılaştırması
- Leave-one-work-out etki tablosu
- Genre, audience, adaptation, edition ve source confound raporu
- FAIR-oriented tekrar üretim paketi

Hak ve veri koşulları:

- Kamu malı yazar statüsü, modern edisyon veya dijital transkripsiyonun serbestçe dağıtılabildiği anlamına gelmez.
- Metin, tarama, transkripsiyon, TEI/markup, anotasyon ve derived outputs için ayrı hak alanı tutulur.
- `unknown` veya `permission_required` durumundaki ham metin public demo ya da export paketine girmez.
- PhiloEditor platformunun veya ATLAS kaydının CC BY 4.0 etiketi, 1983 Castellani Pollidori metninin yeniden dağıtım izni olarak varsayılmaz.
- Kaynak, kompozisyon tarihi, ilk yayın, kullanılan edisyon, temizlik, lisans ve checksum DATA-SOURCES.csv içinde tutulur.
- Noktalama normalizasyonu bilinen kaynaklarla punctuation-based autorial sonuç kurulmaz.

Pinokyo TÜBİTAK projesi ile Delta demo corpus'u ayrı araştırma nesneleridir. Veri veya yayın örtüşmesi oluşursa açıkça kaydedilir.

## 9. FAIR-by-Design

Arayüz ve makale FAIR Package yerine FAIR-oriented reproducibility package der. FAIR, open ile aynı şey değildir ve kalite sertifikası değildir.

Her release için hedef metadata:

~~~text
metadata/
  CITATION.cff
  codemeta.json
  .zenodo.json
  ro-crate-metadata.json
  RIGHTS.md
  rights.json
  DATA-SOURCES.csv
locks/
  python.lock
  renv.lock
  container-digest.txt
~~~

Her analiz koşumu için hedef yapı:

~~~text
runs/<run_uuid>/
  manifest.json
  parameters.json
  environment.json
  processing_log.json
  corpus_health.json
  checksums.sha256
  methods.md
  limitations.md
  rerun_instructions.md
  data_availability.md
  results/
  figures/
~~~

Default export ham metin içermez. Ham metin yalnız açık opt-in ve hak kontrolüyle eklenebilir. Feature matrix derived data olarak etiketlenir.

`rights.json` yalnız eser düzeyinde tek lisans alanı tutmaz. Her kaynak için en az şu asset katmanlarını ayrı kaydeder:

- underlying work
- source edition
- scan veya image
- transcription
- TEI veya başka markup
- scholarly annotations
- normalized text
- derived features ve results

Her katman `permitted`, `restricted`, `permission_required` veya `unknown` durumlarından birini alır. `permission_required` ve `unknown` ham varlıklar public export, demo bundle veya repository release içine giremez. Metadata ve izin veriliyorsa checksum yayımlanabilir.

Release akışı:

1. Tek kanonik sürüm kaynağı
2. Git tag ve immutable commit
3. Metadata ve lock doğrulama
4. Software Heritage snapshot ve SWHID
5. RO-Crate ve checksum üretimi
6. Zenodo concept DOI ve version DOI
7. Canlı site, repo, CFF, DOI ve app version eşlik kontrolü

## 10. AI ve Geliştirme Provenance'ı

Runtime analizinde AI kullanılmaz. Claude ve Codex geliştirme, test, dokümantasyon veya araştırma desteğinde kullanılabilir ve bu kullanım açıklanır.

Altı kimlik birbirine karıştırılmaz:

- PromptEvent: tek gerçek kullanıcı mesajı
- Ticket: geliştirme işi
- HumanDecision: insan-owned yöntem, claim veya acceptance kararı
- Commit: Git nesnesi
- ADR: karar ve gerekçesi
- Run: bilimsel analiz koşumu

Prompt event alanları:

- Event ID
- UTC zaman
- Model, provider ve surface
- Session ID mevcutsa
- Request ve response hashleri
- İlişkili ticket, ADR ve commit
- recording_mode=native|transcribed|reconstructed
- Redaction durumu ve gerekçesi

Tam model yanıtlarını yayımlamak zorunlu değildir. Özel arşivde saklanıp kamuya hash, redaksiyon ve sonuç özeti verilebilir. Retrospektif kayıt native veya exact diye etiketlenemez.

### 10.1 Scholarly Vibe Coding

Delta, formal Python yazılım geliştirme uzmanlığı başlangıç koşulu olmayan bir edebiyat ve DBB araştırmacısı tarafından Claude ve Codex yardımıyla geliştirilmektedir. Proje bu scholar-led, evidence-gated AI-assisted development biçimini **scholarly vibe coding** olarak adlandırır.

Bu modelde Oğuz; araştırma sorusu, corpus, yöntem, haklar, yorum sınırları, acceptance kriterleri, claim ve release kararlarının sahibidir. AI ajanları kod, test, şema, dokümantasyon ve adversarial review üretir. AI kendi çıktısını tek başına bilimsel olarak onaylayamaz; kabul için otomatik test, doğrudan `stylo` parity, fixture, claim gate ve gerektiğinde başka ajan denetimi gerekir.

“Formal Python uzmanlığı olmadan geliştirme” bir öz-konumlanma beyanıdır. Oğuz'un hiçbir Python bilgisi olmadığı, süreç içinde hiçbir şey öğrenmediği, programlama uzmanlığının gereksiz olduğu veya her araştırmacının aynı sonucu elde edeceği iddia edilmez.

P001'den itibaren human-decision ledger tutulur. Her ticket; insan tarafından sahiplenilen kararları, AI önerilerini, kabul/red gerekçelerini, acceptance sonucunu ve ilişkili PromptEvent/Commit/ADR/Run kimliklerini taşır. Ayrıntılı karar ADR-0008'dedir.

## 11. Hafıza ve Bağlam Sürekliliği

Bağlam sıkıştırmasından hemen önce kayıt almaya güvenilmez. Sıkıştırma önceden haber vermeyebilir.

Kalıcı hafıza katmanları:

1. DEVELOPMENT_CONTRACT.md: değişmeyen kanonik sözleşme
2. decisions/: karar ve gerekçeler
3. PROJECT_MEMORY.md: uzun ömürlü proje bağlamı, reddedilen seçenekler ve açık sorular
4. SESSION_HANDOFF.md: o anda nerede kalındığını gösteren kısa panel
5. memory/checkpoints/: yalnız kritik dönüm noktalarının tarihli özetleri
6. Git geçmişi: dosya değişikliklerinin kalıcı izi

Güncelleme tetikleyicileri:

- Kullanıcı bir ürün veya yöntem kararını onayladığında
- Bir ADR kabul edildiğinde
- Kodlama aşaması değiştiğinde
- Bir test veya hakem bulgusu sözleşmeyi etkilediğinde
- Ajan değişimi veya uzun iş devri öncesinde
- Oturum kapanırken

Tam sohbet dökümü proje hafızasına yığılmaz. Kritik kullanıcı ifadeleri, karar, gerekçe, alternatif, kanıt ve sonuç kaydedilir. Tam transkript için Codex veya Claude uygulamasının konuşma geçmişi ikincil arşivdir.

Yeni veya sıkıştırma sonrası bir ajan şu sırayla okur:

1. AGENTS.md veya CLAUDE.md
2. START_HERE.md
3. SESSION_HANDOFF.md
4. Roadmap içindeki aktif ticket bölümü
5. Ticket'ın işaretlediği claim, threat, ADR ve ilgili kod/testler

DEVELOPMENT_CONTRACT.md ve PROJECT_MEMORY.md; mimari/yöntem değişikliği, belge çelişkisi, P000/P015 kapanışı veya release kararında tamamen okunur.

## 12. Güvenlik ve Gizlilik

Upload savunmaları:

- Extension, MIME ve içerik uyumu
- Path traversal, absolute path, nested archive, symlink ve hardlink reddi
- ZIP bomb, açılmış toplam boyut ve dosya sayısı limiti
- Null byte, duplicate normalized filename ve NFC/NFD çakışması kontrolü
- Binary payload ve bozuk encoding reddi
- CSV formula, newline ve path injection kontrolü

R çalıştırma:

- shell=False
- Sabit argv
- Temiz environment
- Kapalı stdin ve ağ erişimi
- Belirli cwd
- Timeout ve tüm process tree cleanup
- Job başına CPU ve bellek sınırı
- Ham metni stdout, stderr veya loglara yazmama

Retention politikası:

- Raw upload ve normalize metin, export üretildikten sonra terminal job state'inde silinir.
- İndirilebilir export mümkünse session memory'de tutulur; disk gerekiyorsa en fazla 1 saat TTL uygulanır.
- Başarısız job çalışma alanı en fazla 15 dakika içinde silinir.
- Silme defteri yalnız job ID, zaman, byte/dosya sayısı ve neden tutar.
- Güvenlik logları en fazla 7 gün tutulur ve metin veya metadata içeriği barındırmaz.
- Privacy metni gerçek uygulamayla birebir aynı olmalıdır.

## 13. Deployment

Delta mevcut Hetzner VPS'i paylaşabilir, fakat servis düzeyinde tamamen ayrılır:

- Ayrı Unix user
- Ayrı Python environment
- Ayrı R ve renv environment
- Ayrı systemd service
- Ayrı port, varsayılan 127.0.0.1:8502
- Ayrı job ve state dizinleri
- Ayrı CPU, memory ve timeout limitleri
- Aynı anda 1 çalışan ve en fazla 3 bekleyen R job
- XSRF ve CORS korumaları açık
- Immutable release artifact ve gerçek rollback provası

lda.lemmata.app koduna, environment'ına, portuna ve verisine dokunulmaz. Delta release'i hem Delta hem LDA smoke testini geçmeden tamamlanmış sayılmaz.

## 14. Makale Sözleşmesi

Makale tool-first, evidence-led bir DBB yazısıdır. Pinokyo ana araştırma nesnesi değil, worked example'dır.

Kanonik ana tez:

> No-code access is not methodologically sufficient. Delta shows how a scholar-led interface can make corpus confounds, parameter sensitivity, interpretive limits, and reproducibility first-class outputs of literary stylometry.

Türkçe anlamı:

> Kodsuz erişim tek başına yöntemsel yeterlilik sağlamaz. Delta'nın katkısı styloyu yalnız tarayıcıya taşımak değil; corpus kararlarını, parametre duyarlılığını, alternatif açıklamaları, yorum sınırlarını ve yeniden üretim kanıtını analizin zorunlu çıktıları haline getirmektir.

Makalenin cevaplayacağı üç soru:

1. Kod bilmeyen araştırmacılar için teknik eşiği kaldırırken yöntemsel kararlar nasıl görünür tutulabilir?
2. Delta, kilitli koşullarda R stylo ile hesaplama eşliği, benchmark performansı ve temiz ortamda tekrar üretim gösterebilir mi?
3. Collodi Before and After Pinocchio örneği, kronolojik stilometrik bir örüntünün corpus ve parametre kararlarına bağlılığını nasıl görünür kılar?

İkincil refleksif yöntem sorusu:

> How can a literary scholar without prior formal proficiency in Python software development use AI-assisted development while retaining methodological ownership, auditability, and responsibility for scientific claims?

Bu soru ana tool tezinin yerine geçmez. Provenance coverage yeterliyse development case olarak, yetersizse yalnız yöntem/disclosure ve sınırlılık notu olarak raporlanır.

Makalenin yeniliği yeni bir Delta metriği değildir. Yenilik; uncertainty, confound audit, parameter stability, interpretive guardrails ve FAIR-oriented run package bileşenlerinin kodsuz tek bir scholar-led workflow içinde birleştirilmesi ve katmanlı kanıtla değerlendirilmesidir.

Kanıt kapıları geçmeden kullanılacak önerilen başlık:

> Delta: An Uncertainty-Aware and Reproducibility-Oriented No-Code Stylometry Workbench for Digital Humanities

Olası alt başlık:

> Design, Validation, and a Collodi Style-Over-Time Worked Example

`Reproducible` başlık veya ana claim'e ancak claim-evidence matrisindeki CE-11 ve CE-12 kapıları birlikte geçerse alınabilir.

Makalenin ana katkıları:

1. Alan uzmanı tarafından yönlendirilen ürün ve epistemik guardrail tasarımı
2. Parametre duyarlılığını kullanıcı arayüzüne taşıyan protokol
3. Metadata-aware ve confound-aware Style Over Time akışı
4. stylo parity, known-author benchmark, diachronic benchmark, negative control ve tekrar üretim kanıtları
5. FAIR-oriented run package
6. Pinokyo öncesi ve sonrası Collodi corpus'uyla halka açık worked example
7. Scholar-led ve evidence-gated scholarly vibe coding sürecinin şeffaf development case'i; yalnız provenance coverage yeterliyse

Pinokyo bölümü toplam metnin yaklaşık %10-15'ini geçmez. Scholarly vibe coding başlıkta veya ana ürün katkısında yer almaz; yöntem, provenance, AI disclosure ve sınırlılıklar içinde ikincil refleksif katkı olarak belirtilir.

Önerilen yapı:

1. Problem ve kullanıcı grubu
2. Related tools, PhiloEditor görev sınırı ve araştırma boşluğu
3. Scholar-led design ilkeleri
4. Mimari ve metodoloji
5. Computational ve empirical validation
6. Collodi Before and After Pinocchio worked example
7. FAIR, provenance, scholarly vibe coding ve AI disclosure
8. Expert evaluation, sınırlılıklar ve sonuç

Hedef dergi Umanistica Digitale'dir. Ana metin tercihen profesyonel son okumadan geçmiş İngilizce; İtalyanca abstract ve keywords ayrıca hazırlanır. Makale yazımına geçmeden akademik asistanın zorunlu 20 soruluk hazırlık turu tamamlanır.

Yazarlık ve roller:

- Oğuz Koran: birinci ve sorumlu yazar; conceptualization, methodology, scholar-led software development, corpus curation, investigation, visualization, human acceptance, original draft
- Barış Yücesan: ikinci yazar; validation, structured expert walkthrough, Pinokyo corpus değerlendirmesi, yöntem eleştirisi, writing-review
- Hakan Cangır: yalnız benchmark ve istatistiksel doğrulamanın sahipliğini fiilen üstlenirse üçüncü yazar adayı
- Claude ve Codex: yazar değildir; AI-assisted development disclosure içinde belirtilir

Hedef takvim:

- Temmuz-Ağustos 2026: uygulama geliştirme
- Eylül-Ekim 2026: benchmark, Collodi corpus'u ve rights audit
- Kasım 2026: Barış expert walkthrough ve acceptance test
- Aralık 2026: FAIR-oriented release ve clean-room rerun
- Ocak 2027: makale yazımı ve profesyonel İngilizce son okuma
- Şubat 2027: Umanistica Digitale gönderimi

Takvim bir kalite kapısını kaldırmaz. Rights, validation, rerun veya acceptance kanıtı eksikse gönderim ötelenir.

## 15. Geliştirme Kapıları

P000, 2026-07-10 tarihinde `docs/development/p000-closure.md` kaydıyla kapatılmıştır. P001 de 2026-07-10 tarihinde `provenance/evidence/P001/report.md` ile acceptance kapısını geçmiştir. P002 veya başka ticket ancak kendi Ticket ve PromptEvent kaydı açıldıktan sonra uygulanır.

P000 çıktıları:

- Kapsam ve claim-evidence matrisi: `docs/research/claim-evidence-matrix.md`
- Tehdit modeli ve retention tablosu: `docs/security/threat-model.md`
- Desteklenen environment matrisi: `docs/development/supported-environments.md`
- Metodoloji ve stability eşik protokolü: ADR-0002 ve ADR-0005
- Pinokyo demo corpus planı ve rights gate: `docs/methodology/pinocchio-diachronic-worked-example.md` ve ADR-0004
- PhiloEditor görev sınırı ve Style Over Time confound protokolü: ADR-0004 ve kanonik sözleşmenin 6.7/8. bölümleri
- Scholarly vibe coding ve human-decision provenance: ADR-0008 ve CE-20
- P001-P015 acceptance ve bağımlılık haritası: `docs/development/roadmap-P001-P015.md`
- Ajan başlangıç yönlendirmesi: `START_HERE.md`
- Kullanıcı kararı gerektiren açık P000 bloklayıcısı: sıfır

P001 çıktıları:

- Bağımsız Git repository ve repo sınırı: ADR-0009
- Kilitli Python/R ortamları, metadata, provenance şemaları ve CI/security scaffold'u
- Temiz Git klonunda tek komut bootstrap ve 24 testlik doğrulama
- Machine-readable Ticket, PromptEvent, HumanDecision ve Run kayıtları
- Açık sınırlamalar: Docker build/CI remote çalışması ve gerçek `stylo` parity henüz doğrulanmadı

Kilitli sıra ve ayrıntılı acceptance koşulları `docs/development/roadmap-P001-P015.md` içindedir. Kısa sıra:

- P001: Repository, locks, metadata ve provenance scaffold
- P002: English-only workbench shell
- P003: Secure ingestion
- P004: Metadata, corpus inventory ve rights
- P005: Job lifecycle, isolation ve retention
- P006: R stylo worker ve computational parity
- P007: Preprocessing ve corpus health
- P008: Guided ve Research workflows
- P009: Results, explanations ve interpretive guardrails
- P010: Benchmarks, negative controls ve leakage audit
- P011: Parameter stability ve calibration
- P012: FAIR-oriented export ve clean rerun
- P013: Pinokyo diachronic worked example
- P014: Isolated deployment, load ve rollback
- P015: Expert walkthrough, FAIR release ve publication readiness

Her ticket için zorunlu kapanış kanıtı:

- Değişen dosyalar
- Test komutu ve gerçek sonuç
- İlgili ADR ve prompt event bağlantısı
- Claim-evidence güncellemesi
- SESSION_HANDOFF.md güncellemesi

## 16. Bitmiş Sayılma Koşulu

Delta şu koşullar birlikte sağlanmadan bitmiş sayılmaz:

- Kilitli temiz kurulum başarılı
- stylo parity başarılı
- Known-author ve negative-control raporları mevcut
- Diachronic benchmark ve Style Over Time confound raporu mevcut
- Pinokyo worked example hak ve veri manifesti tamam
- Barış Yücesan structured expert walkthrough ve acceptance checklist'i tamamlamış
- Default export ham metin içermiyor ve checksum doğrulanıyor
- Bağımsız rerun başarılı
- Privacy ve retention uygulamayla aynı
- Canlı Delta ve LDA smoke testleri başarılı
- Sürüm, commit, CFF, CodeMeta, DOI ve site metadata aynı release'i gösteriyor
- Kullanıcıya sunulan her bilimsel iddianın bir test, run veya kaynak kanıtı var
