# ADR-0004: Pinocchio as the Public Worked Example

**Durum:** Kabul edildi  
**Tarih:** 2026-07-10  
**Revizyon:** 2026-07-10, authorship demo yerine diachronic worked example

## Bağlam

Pinokyo tanınmış ve Umanistica Digitale okuyucusuna anlaşılır bir örnek sağlar. Yine de makaleyi Pinokyo araştırmasına dönüştürmek Delta'nın tool-first amacını zayıflatır.

İlk karar Pinokyo parçalarını known-answer unknown olarak kullanmayı ve Collodi reference eserleriyle yazarlık yakınlığı göstermeyi öngörüyordu. Kaynak denetimi, karşılaştırılabilir bağımsız Collodi eserlerinin ve tutarlı dijital edisyonların bu amaç için yetersiz veya hak bakımından belirsiz olabileceğini gösterdi. Ayrıca bu deney zaten bilinen yazarı yeniden bulmaktan öte güçlü bir ürün katkısı sunmuyordu.

PhiloEditor aynı Pinokyo eserinin 1881-1883 tefrikası ile 1983 kritik edisyonunu word-based diff, varyant gösterimi ve anotasyonla karşılaştırır. Delta'nın bu sürümleri karşılaştırması ürün sınırını bulanıklaştırır.

## Karar

Pinokyo Delta'nın public, FAIR-oriented Style Over Time worked example'ı olacaktır. Unknown authorship demo kararı geçersizdir. Güçlü `reproducible` claim'i ancak clean-room ve package kapıları geçerse kullanılır.

Demo adı:

> Collodi Before and After Pinocchio: Is the Apparent Stylistic Shift Robust?

Delta, Collodi'nin farklı tarihlerde yayımlanmış bağımsız eserlerini work-level stilometrik uzayda inceler. Pinokyo seçili kronolojide bir pivot gözlemidir. Amaç Pinokyo'nun kesin bir edebî dönüm noktası olduğunu kanıtlamak değil, bu görünümün tür, hedef kitle, edisyon, tek-eser etkisi ve parametre seçimlerine ne kadar bağlı olduğunu göstermektir.

İki corpus katmanı kullanılır:

- Audience-controlled core: 1877-1890 çocuk ve genç okur eserleri
- Broad career panorama: 1856-1890, tür ve hedef kitle karışması nedeniyle exploratory

Yalnız ilk ve son eser karşılaştırılmaz. En az üç kronolojik nokta ve toplam altı bağımsız eser olmadan sonuç exploratory sayılır.

PhiloEditor sınırı:

- Delta sürüm hizalama veya diff yapmaz.
- Varyant göstermez veya sınıflandırmaz.
- Anotasyon, TEI edisyonu veya kritik edisyon üretmez.
- İki Pinokyo sürümünü v0.1 demosunda karşılaştırmaz.
- PhiloEditor yalnız related work ve kaynak eleştirisi bağlamında anılır.

## Koruyucu Koşullar

- Edisyon, transkripsiyon, markup ve derived-output haklarının ayrı kontrolü
- Source, date, rights ve cleaning manifesti
- Audience-controlled core ile broad panorama sonuçlarının ayrı verilmesi
- Genre, audience, adaptation, collection, edition ve source confound audit
- Segmentlerin bağımsız eser sayılmaması
- Leave-one-work-out etki testi
- Parametre eşiklerinin Pinokyo run'ından önce benchmark üzerinde dondurulması
- Pinokyo sonucunun tek başına tool validation sayılmaması
- Hak durumu `unknown` veya `permission_required` olan ham metnin public export'a girmemesi

## Sonuç

PhiloEditor yerel metinsel varyantları, Delta bağımsız eserler arasındaki global stilometrik konumu ve kanıt kararlılığını inceler. Worked example'ın başarı ölçütü belirgin bir zaman farkı bulması değil, bulgunun hangi koşullarda korunmadığını da dürüstçe göstermesidir.

Ayrıntılı protokol: `docs/methodology/pinocchio-diachronic-worked-example.md`

## İlişkili Proje

Akademik asistan içinde ayrı bir Pinokyo Türkiye'de TÜBİTAK projesi bulunmaktadır. Delta demo corpus'u o projenin yayın veya veri çıktısı gibi sunulmaz; olası örtüşme ayrıca kaydedilir.
