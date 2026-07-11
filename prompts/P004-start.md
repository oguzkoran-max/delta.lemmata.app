# P004 Execution Brief

**Kayıt türü:** Agent-prepared, human-owned ticket execution brief

**PromptEvent değildir:** Kullanıcının native isteği ayrı PromptEvent içinde hash ile
kayıtlıdır. Bu dosya, kısa devam isteğinin daha önce onaylanan roadmap ve proje
sınırları içindeki teknik açılımıdır; native kullanıcı mesajı gibi sunulmaz.

```text
P004: Metadata, Corpus Inventory, and Rights

START_HERE.md ve SESSION_HANDOFF.md dosyalarını oku. Ardından roadmap'teki yalnız
P004 bölümünü, claim CE-09 ve CE-13'ü, threat RP-01, RP-02, EPI-01 ve EPI-07'yi,
P003 Ticket kapanış sınırını ve Pinocchio diachronic worked example metadata
notlarını incele. Daha önce onaylanmış ürün kararlarını yeniden sorma.

Önce P004 Ticket ve gerçek devam isteğine ait PromptEvent kaydını doğrula. Sonra:

1. Her corpus metnini dosya, asset, bağımsız eser, edisyon ve kaynak katmanlarını
   karıştırmadan tanımlayan sürümlü bir metadata modeli kur.
2. Genel modelde en az file/asset eşlemesi, `work_id`, title, author, language,
   work chronology, date certainty, edition, genre, audience, adaptation,
   collection, source ve normalization alanlarını tanımla. Style Over Time için
   kronoloji alanlarını açık ve doğrulanabilir yap.
3. `verified-open`, `analysis-only`, `permission-required`, `unknown` ve `excluded`
   durumlarını içeren asset-level rights state machine kur. Bu durum tek başına
   eylem izni sayılmasın.
4. Upload, analysis, export ve public redistribution izinlerini ayrı, üç değerli
   veya daha güvenli bir modelle kaydet. Belirsizlik hiçbir aşamada izin gibi
   yorumlanmasın. Public raw/normalized text ancak gerekli hak katmanlarının hepsi
   açıkça izinliyse uygun sayılsın.
5. Versioned CSV template, field dictionary, valid/invalid fixtures ve satır/alan
   düzeyinde düzeltilebilir validation raporu üret. Eksik zorunlu alan, duplicate
   `work_id`, eşleşmeyen filename, çelişkili tarih, bilinmeyen enum veya hak durumu
   fail-closed sonuç versin.
6. Corpus inventory'yi canonical sıraya koy ve deterministik hash üret. Dosyaların
   upload sırası hash'i değiştirmesin; semantik metadata değişikliği hash'i
   değiştirsin ve önceki run bağını geçersiz kılacak açık contract sağlasın.
7. Style Over Time readiness kuralını modelle: en az üç kronolojik nokta ve altı
   bağımsız eser yoksa sonuç üretme aşamasına `exploratory` zorunluluğu taşı.
   Bu eşik bilimsel yeterlilik garantisi veya confound giderimi olarak sunulmasın.
8. İngilizce workbench'te form + CSV, progressive disclosure, exact eşleştirme ve
   Corpus Review akışını `docs/development/p004-metadata-ux-decisions.md` kararlarına
   göre bağla. Review ekranında work timeline, composition bars, rights action
   matrix, metadata completeness matrix ve readiness summary kullan. P003 secure
   intake sınırını gevşetme, rejected payload saklama veya P004'te stilometrik sonuç
   grafiği taklit etme.
9. Determinism, rights negative fixtures, schema migration, malformed CSV,
   cross-field tarih kuralları, upload-order invariance ve metadata invalidation
   testlerini ekle. Measured source için yüzde 100 statement/branch coverage
   kapısını koru.
10. Başarısız denemeleri, kararları, testleri ve sınırları P004 evidence paketinde
    sakla. İnsan hak/metadata terminolojisi denetimi ve exact-commit clean-clone
    doğrulaması olmadan P004'ü complete yapma.

Otomatik hukuki hüküm, internetten corpus toplama, job retention, gerçek R stylo
analizi, nihai Pinocchio corpus araştırması, deployment, runtime AI veya
lemmata.app Launch Stylometry entegrasyonu uygulama. Metadata ya da hak belirsizliği
varsa sistemi sessizce açık kabul ettirme.
```
