# ADR-0011: Versioned Single-Upload Metadata CSV

**Durum:** Kabul edildi; P004 acceptance değildir

**Tarih:** 2026-07-12

**Kapsam:** P004 metadata CSV representation, secure import/export, and round-trip identity

## Bağlam

P004 domain modeli author, work, edition, source, analyzed asset, immutable P003 file
projection ve çok katmanlı rights kayıtlarını birbirinden ayırır. Kabul edilmiş ürün
sözleşmesi hem guided on-screen editor hem versioned CSV import/export ister. P003
aynı batch içinde yalnız bir optional metadata CSV kabul eder ve en fazla 64 sütuna
izin verir.

Bir CSV tasarımı şu koşulları aynı anda sağlamalıdır:

- normal bibliyografik alanlar spreadsheet içinde okunabilir kalmalı;
- multiple contributors, authority identifiers ve rights dependency layers kaybolmamalı;
- custom delimiter veya noktalama üzerinden ad hoc parsing yapılmamalı;
- exact P003 file label ve SHA-256 bağı korunmalı;
- generated export güvenlik sınırını aşmamalı;
- canonical semantic payload ve inventory hash round trip sonrasında aynı kalmalı.

## Karar

- CSV version `corpus-metadata-csv-v1` olacaktır.
- Her analyzed work bir satırdır. v0.1'de bir analyzed TXT bir independent work
  olduğu için satır birimi domain modeliyle aynıdır.
- Sözleşme 58 fixed column kullanır ve P003 64-column limitinin altında kalır.
- Normal identity, chronology, classification, edition, source, normalization,
  confirmation ve intake değerleri plain columns olarak tutulur.
- Yalnız one-to-many yapılar standard compact JSON arrays kullanır:
  `primary_author_authorities_json`, `additional_contributors_json`,
  `rights_sources_json` ve `rights_records_json`.
- `rights_sources_json`, bir hak katmanının kaynağı analiz edilen metnin edinim
  kaynağından farklı olduğunda tam source kaydını korur.
- Generated field-dictionary schema v1'in bütün 58 position/name değerini exact
  ordered `prefixItems` olarak uygular; dış tüketici daha gevşek sözleşme kullanamaz.
- Header order importta değişebilir; column names exact dictionary ile eşleşmelidir.
  Export her zaman canonical order üretir.
- P003 catalog CSV'nin içinden türetilmez. Exact file label, content SHA-256,
  intake profile ve status ayrı validated catalog ile karşılaştırılır.
- Template teknik identifier önerilerini exact file label digest ve content hash ile
  üretir; title, author, source, dates veya rights hakkında scholarly guess yapmaz.
- JSON duplicate keys, non-standard constants, excessive nesting, Unicode-escaped
  unsafe values, formula prefixes, HTML, newline, path, BOM, bidi controls ve NFC dışı
  strings fail-closed reddedilir.
- Import failure partial inventory döndürmez ve cell value yankılamaz. Parse sonrası
  domain blockers inventory ile birlikte row-aware validation report olarak kalır.
- Export duplicate stable identifiers ve unresolved references için fail-closed olur.
  Generated scalar ve nested values P003 policy ile yeniden doğrulanır.
- Public redistribution yalnız verified-open status, export permission, license,
  jurisdiction ve URL evidence birlikte mevcutsa açılır; statement-only claim yetmez.
- Round-trip claim UI tuple order değil canonical semantic identity üzerindedir:
  canonical payload, inventory SHA-256 ve canonical re-export aynı kalmalıdır.

## Alternatifler

### Multiple CSV Tables veya ZIP Bundle

Reddedildi. Relational yapıyı temiz ifade eder, fakat kabul edilmiş single metadata
CSV upload boundary ile çelişir ve beginner workflow için ek file-management yükü
yaratır.

### Long-Form `record_type` CSV

Reddedildi. Her entity'yi temsil edebilir, fakat sparse polymorphic rows normal
spreadsheet editing ve field-level help'i zorlaştırır.

### Bütün Nested Yapıları Delimited Text Olarak Tutmak

Reddedildi. Contributor names, citations ve evidence punctuation içerdiği için custom
split/escape grammar veri kaybı ve parser belirsizliği üretir.

### Unsafe Değerleri Reversible Escape ile Geçirmek

Reddedildi. P003'ün reddettiği HTML, path veya formula-like metadata'yı başka encoding
ile yeniden kabul etmek güvenlik sınırını anlamsızlaştırır. Kullanıcı unsafe değeri
düzeltmelidir.

## Sonuçlar

- Common-case spreadsheet 58 sütunla geniştir; guided editor beginner surface olarak
  kalır, CSV bulk/expert surface'tir.
- Full invalid inventories içindeki orphan veya duplicate top-level records güvenilir
  biçimde export edilmez. Export conflicting identities arasından seçim yapmaz.
- Set-like authority, contributor, dependency ve evidence sırası canonicalize edilir.
  Bu nedenle arbitrary UI tuple order round-trip iddiasına dahil değildir.
- Field dictionary executable package data, generated JSON Schema, blank template,
  valid/invalid fixtures ve tests aynı contract version'a bağlıdır.
- Bu ADR yalnız implementation architecture'ı kabul eder. P004 UI, rights
  questionnaire, graphics, browser evidence ve Oğuz Koran human acceptance kapıları
  ayrı kalır.
- İlk 57-column/üç JSON-field taslağındaki ayrı rights-source kaybı independent
  adversarial review sırasında bulundu. Bu ADR aynı row modelini koruyarak 58-column/
  dört JSON-field biçimine düzeltildi; bu teknik düzeltme P004 human acceptance iddiası
  değildir.

## Kanıt Bağlantıları

- `HD-20260711-0011`
- `docs/development/p004-metadata-csv.md`
- `src/delta_lemmata/data/corpus-metadata-fields-v1.json`
- `schemas/corpus-metadata-field-dictionary.schema.json`
- `templates/corpus-metadata-v1.csv`
- `tests/test_metadata_csv.py`
