# Pinocchio Diachronic Worked Example Protocol

**Durum:** Tasarım kabul edildi, kaynak ve hak denetimi bekleniyor  
**Tarih:** 2026-07-10  
**İlgili karar:** decisions/ADR-0004-pinocchio-worked-example.md

## 1. Amaç

Bu protokol Delta'nın halka açık Pinokyo örneğini tanımlar. Örnek bir Pinokyo araştırma makalesi veya yazar tespiti deneyi değildir. Delta'nın Style Over Time akışını, corpus denetimini, parametre kararlılığını, yorum sınırlarını ve FAIR-oriented export'unu göstermelidir.

Demo adı:

> Collodi Before and After Pinocchio: Is the Apparent Stylistic Shift Robust?

Ana soru:

> Hakları denetlenmiş seçili Collodi corpus'unda eserlerin stilometrik konumları yayın kronolojisi boyunca nasıl değişir ve Pinokyo'nun olası bir dönüm noktası gibi görünmesi tür, hedef kitle, edisyon ve parametre denetimlerinden sonra korunur mu?

Burada "dönüm noktası", edebiyat tarihi açısından kanıtlanmış bir kırılma anlamına gelmez. Yalnız Pinokyo'nun seçili eserler arasındaki göreli stilometrik konumunu anlatır.

## 2. Neden İlk ve Son Eser Yetmez?

Collodi'nin ilk yayımlanan eseri ile son eserini karşılaştırmak kolay, fakat yöntemsel olarak zayıftır. Bulunan fark şu nedenlerden herhangi biriyle oluşabilir:

- zaman
- tür
- hedef kitle
- konu
- eser uzunluğu
- uyarlama veya çeviri durumu
- kullanılan baskı
- editör veya transkripsiyon
- OCR ve normalizasyon politikası

Bu nedenle Delta yalnız iki metni karşılaştırıp "üslup zaman içinde değişti" demez. En az üç kronolojik nokta, toplam en az altı bağımsız eser ve mümkün olduğunda benzer hedef kitleli bir core corpus ister.

## 3. PhiloEditor'dan Kesin Ayrım

PhiloEditor ile Delta aynı görevi yapmaz.

| Boyut | PhiloEditor | Delta |
|---|---|---|
| Araştırma nesnesi | Aynı eserin farklı redaksiyonları | Farklı tarihlerde yayımlanmış bağımsız eserler |
| Temel soru | Metnin hangi bölümleri değişti? | Görülen global stilometrik örüntü hangi koşullarda korunuyor? |
| Yöntem | Word-based diff ve varyant sınıflandırma | MFW, Burrows Delta, work-level distance ve kararlılık |
| Çıktı | Ekleme, silme, yerel varyant, anotasyon | Stilometrik konum, kronolojik harita, confound ve duyarlılık raporu |
| Kullanıcı işi | Edisyonları okuma, karşılaştırma ve anotasyon | Corpus kurma, deney çalıştırma ve kanıtı denetleme |
| TEI rolü | Edisyon ve anotasyon çıktısı | Provenance girdisi; v0.1'de genel TEI ingestion yok |

Delta'da şu işlevler bulunmaz:

- İki sürümü sözcük sözcük hizalama
- Ekleme ve silmeleri renklendirme
- Varyantları sınıflandırma
- Satır içi veya interlinear karşılaştırma
- İki sütunlu edisyon görünümü
- Kritik edisyon veya kişisel edisyon üretme
- PhiloEditor arayüzünü taklit etme

Kısa görev ayrımı:

> PhiloEditor "Nereler değişti?" sorusunu cevaplar. Delta "Bağımsız eserler arasında görülen stilometrik yönelim, alternatif açıklamalar ve parametre değişiklikleri karşısında korunuyor mu?" sorusunu cevaplar.

PhiloEditor related work olarak açıkça anılır. Verisi Delta'nın zorunlu kaynağı değildir ve iki Pinokyo sürümünün karşılaştırılması v0.1 demosuna alınmaz.

## 4. Corpus Tasarımı

### 4.1 Audience-Controlled Core

Amaç, çocuk ve genç okura yönelik eserlerle hedef kitle farkını kısmen azaltmaktır. Bu set tür bakımından tam dengeli değildir; eğitim kitabı, anlatı ve derleme farkları ayrıca raporlanır.

Hak ve edisyon denetimine bağlı adaylar:

| Rol | Eser | İlk yayın | Kritik not |
|---|---|---:|---|
| Pinokyo öncesi | Giannettino | 1877 | Parravicini'nin Giannetto'sunun kapsamlı yeniden yazımı; adaptation_status zorunlu |
| Pinokyo öncesi | Minuzzolo | 1878 | Giannettino serisiyle bağımlılık açıkça işaretlenir |
| Pivot | Le avventure di Pinocchio | 1881-1883 | Hakları açık tek bir tanık seçilir; pivot tek başına dönem sayılmaz |
| Pinokyo sonrası | Il regalo del Capo d'Anno | 1884 | 1887'de farklı başlıkla yeniden basım bilgisi kaydedilir |
| Pinokyo sonrası | Storie allegre | 1887 | Önceden yayımlanmış anlatılar ve değişken 20. yüzyıl içerikleri denetlenir |
| Pinokyo sonrası | La lanterna magica di Giannettino | 1890 | Eğitim serisinin son halkası; tür farkı raporlanır |

Core corpus yalnız şu kapılar geçilirse birincil örnek olur:

- Altı bağımsız work_id
- Pinokyo öncesinde en az iki ve sonrasında en az iki bağımsız eser
- Hakları açık, karşılaştırılabilir dijital tanıklar
- Corpus genelinde tutarlı paratext temizliği
- Eser tarihleri ve edisyon tarihlerinin ayrı kaydı
- Yeniden kullanılan pasajlar için overlap taraması

Kapılar geçilmezse sonuç exploratory olarak yayımlanır.

### 4.2 Broad Career Panorama

Kariyerin daha geniş bölümünü görünür kılmak için aşağıdaki adaylar core corpus'a eklenebilir:

- Un romanzo in vapore (1856)
- I misteri di Firenze (1857)
- I ragazzi grandi (1873), tiyatro uyarlaması geçmişi belirtilerek

Bu panorama erken yetişkin düzyazısı ile geç çocuk ve eğitim metinlerini karşılaştırır. Tarih, tür ve hedef kitle birbirine karıştığı için edebî gelişim veya yaşlanma kanıtı sayılmaz.

### 4.3 Ana Analizden Çıkarılanlar

- I racconti delle fate, çeviri olduğu için
- Divagazioni critico-umoristiche ve Note gaie gibi ağır editörlü posthumous derlemeler
- İlk yayın tarihi ve kullanılan metinsel tanığı ayrı doğrulanamayan derleme parçaları
- Yalnız modern editörlü metni bulunan ve yeniden kullanım izni belirsiz eserler

Macchiette ve Occhi e nasi daha eski metinleri bir araya getirip yeniden işledikleri için otomatik olarak 1880 ve 1881 tarihli bağımsız geç dönem eserleri sayılmaz.

## 5. Zorunlu Metadata

Her eser için:

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
- `text_sha256`
- `clean_text_sha256`

Yayın tarihi bilinip kompozisyon tarihi bilinmiyorsa ikisi eşit varsayılmaz. Arayüz belirsiz tarihi kullanıcıya gösterir.

## 6. Analiz Akışı

1. Item-level hak ve edisyon denetimi yapılır.
2. Paratext, sayfa numarası, editör notu ve görsel açıklamaları ortak politikayla temizlenir.
3. Aynı veya yeniden kullanılan pasajlar eserler arasında taranır.
4. Corpus health ve chronology-confound audit çalışır.
5. Audience-controlled core ve broad panorama ayrı run kimlikleriyle analiz edilir.
6. Guided Mode 100, 300, 500 ve 1000 MFW koşullarını gösterir.
7. Public Research Mode versioned `research-grid-v1` ile en fazla 24 hücre çalıştırır.
8. Publication batch en fazla 192 hücreyi kontrollü ortamda çalıştırabilir.
9. Her eser sırayla çıkarılarak leave-one-work-out duyarlılık testi yapılır.
10. Research Mode'da tarihler eser düzeyinde permüte edilerek keşifsel negatif kontrol uygulanabilir.
11. Sonuçlar, sınırlamalar ve tekrar çalıştırma dosyaları birlikte export edilir.

## 7. Bilimsel Birim ve Segmentasyon

- Bağımsız birim eserdir.
- Segmentler ayrı eser veya bağımsız örnek sayılmaz.
- Segment sayısı fazla olduğu için örneklem büyük denmez.
- Eserler segment sayısıyla orantılı biçimde aşırı ağırlıklandırılmaz.
- Whole-text ve sabit uzunluklu segment koşulları duyarlılık amacıyla karşılaştırılabilir.
- Aynı eserin farklı edisyonları iki bağımsız eser sayılmaz.

## 8. Çıktılar

- Tarih etiketli work-level MDS veya PCA haritası
- Eser düzeyinde distance matrix
- Pinokyo öncesi ve sonrası göreli konum özeti
- Parametre kararlılık heatmap'i
- Leave-one-work-out etki tablosu
- Audience-controlled core ile broad panorama karşılaştırması
- Genre, audience, adaptation, edition ve source confound paneli
- What this shows kartı
- What this does not show kartı
- FAIR-oriented reproducibility package

Tek bir dendrogram sonuç veya kanıt sayılmaz.

## 9. Kararlılık ve Doğruluk Ayrımı

Parametre kararlılığı, aynı genel örüntünün farklı makul ayarlarda ne kadar korunduğunu anlatır. Doğrulukla aynı şey değildir.

Arayüz:

- "yüksek güven" demez
- "yüksek parametre kararlılığı" diyebilir, yalnız eşikler benchmark ile doğrulanırsa
- benchmark ilişkisi yetersizse nitel etiket kullanmaz
- modal konum, rank, margin, co-placement, geçerli feature sayısı ve distance-family yönünü ayrı gösterir

Eşikler diachronic calibration benchmark üzerinde belirlenir. Locked test ve Pinokyo run'ı görülmeden önce dondurulur.

## 10. Dört Ayrı Kanıt Katmanı

| Katman | Kanıtladığı şey | Pinokyo kullanılır mı? |
|---|---|---|
| stylo parity | Delta hesaplarının referans motorla eşliği | Hayır |
| Known-author benchmark | Genel proximity ve classification davranışı | Hayır |
| Diachronic benchmark | Style Over Time protokolünün çok yazarlı veride davranışı | Hayır |
| Pinokyo worked example | Gerçek kullanıcı akışı, yorum sınırı ve export | Evet |

Pinokyo sonucu eşik, metrik veya parametre seçmek için kullanılmaz.

## 11. Hak ve FAIR Kapısı

Kamu malı bir yazarın metni ile belirli bir dijital edisyon aynı hak nesnesi değildir. Her asset ayrı kaydedilir:

- underlying work
- source edition
- scan veya image
- transcription
- TEI veya markup
- scholarly annotations
- normalized text
- derived features ve results

`unknown` veya `permission_required` ham varlıklar public demo, repository veya export paketine girmez.

PhiloEditor sayfası ve ATLAS kaydı platform/dijital edisyon için CC BY 4.0 gösterir. Buna karşılık Fondazione Nazionale Carlo Collodi'nin 1983 Castellani Pollidori metni kişisel ve araştırma kullanımıyla sınırlandırılmış, yayın ve ticari kullanım için yazılı izin istemektedir. Bu nedenle Delta, platform lisansını gömülü kritik metnin yeniden dağıtım izni saymaz.

## 12. İzin Verilen Sonuç Dili

İzin verilen örnek:

> İncelenen corpus içinde yayın kronolojisiyle ilişkili bir stilometrik ayrışma görülmektedir. Bu ayrışmanın gücü hedef kitle kısıtlaması, kullanılan edisyon ve parametre seçimlerine göre değişmektedir. Pinokyo'nun göreli konumu bazı koşullarda korunurken bazı koşullarda zayıflamaktadır.

İzin verilmeyen örnekler:

- "Collodi yaşlandıkça olgunlaştı."
- "Pinokyo Collodi'nin kesin stilistik dönüm noktasıdır."
- "Üslup değişiminin nedeni çocuk edebiyatına geçmesidir."
- "Kümeler Collodi'nin kariyerindeki gerçek dönemleri kanıtlar."
- "Pinokyo'nun tefrika ve kitap farklarını Delta keşfetti."

## 13. Başarı Ölçütü

Worked example'ın başarılı olması için kronolojik fark bulması gerekmez. Başarı şunlardır:

- Analiz hakları açık kaynaklarla tekrar çalıştırılabiliyor.
- Delta corpus karışmalarını sonuçtan önce görünür kılıyor.
- Parametre değişiklikleri sonucu etkiliyorsa bunu saklamıyor.
- Tek bir eser sonucu taşıyorsa leave-one-work-out bunu gösteriyor.
- Araç, gösterilemeyecek edebî ve nedensel iddiaları engelliyor.
- Export başka bir araştırmacı tarafından temiz ortamda yeniden çalıştırılabiliyor.

## 14. Makaledeki Rol

Pinokyo ve Collodi bölümü makalenin yaklaşık yüzde 10-15'ini geçmez. Benchmark sonuçlarından sonra gelir. Bölümün amacı yeni bir Collodi yorumu geliştirmek değil, Delta'nın gerçek bir edebiyat corpus'unda nasıl kullanılacağını ve nerede susması gerektiğini göstermektir.

## 15. Kaynaklar

- PhiloEditor: https://projects.dharc.unibo.it/philoeditor/
- Fondazione Nazionale Carlo Collodi, eser kronolojisi: https://www.fondazionecollodi.it/it/le-opere
- ATLAS, PhiloEditor Pinokyo kaydı: https://projects.dharc.unibo.it/atlas/view-1743001433-3181107
- Fondazione Nazionale Carlo Collodi, 1983 kritik metin kullanım koşulları: https://www.fondazionecollodi.it/assets/it/le-avventure_di_pinocchio.pdf
- Eder, Rybicki ve Kestemont, Stylometry with R: https://journal.r-project.org/articles/RJ-2016-007/index.html
- Cafiero, Ing, Gabay ve Clérice, diachronic benchmark: https://doi.org/10.63744/By09x5ZX3yWX
