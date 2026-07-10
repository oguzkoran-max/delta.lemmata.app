# P003 Start Prompt Template

**Kayıt türü:** Human-reviewed handoff template

**PromptEvent değildir:** Bu dosya henüz Claude veya Codex'e gönderilmiş native
mesaj kanıtı sayılmaz. Gönderildiğinde gerçek içerik, zaman, araç, model ve hash
ayrı PromptEvent olarak kaydedilir.

```text
P003: Secure Ingestion

START_HERE.md ve SESSION_HANDOFF.md dosyalarını oku. Ardından roadmap'teki yalnız
P003 bölümünü, claim CE-14'ü, threat SEC-01/02/03/04/05 kayıtlarını ve P002 Ticket
ile acceptance raporunu incele. Daha önce onaylanmış ürün kararlarını yeniden sorma.

Önce P003 Ticket ve bu gerçek isteğe ait PromptEvent kaydını aç. Sonra:
1. Yalnız .txt, .zip ve metadata .csv kabul eden fail-closed ingestion boundary kur.
2. Extension yerine content-based type validation; UTF-8 ve Unicode NFC kontrolü uygula.
3. ZIP üyesini extraction öncesi denetle; traversal, absolute path, symlink,
   hardlink, nested archive, duplicate filename ve archive bomb risklerini reddet.
4. Boyut, üye sayısı, sıkıştırma oranı, nesting, token ve satır limitlerini merkezi,
   sürümlü config içinde tut; reddedilen input için kaynak ayırma.
5. Kullanıcı filename'ini yalnız escaped display label olarak kullan; storage ve
   workspace kimliklerini sunucu üretsin.
6. CSV formula, HTML, newline, path ve log injection fixture'larını fail-closed işle.
7. Hata mesajını content-free code ile üret; payload, raw text, system path veya
   stack trace'i UI/log içine koyma.
8. Rejected upload sonrasında temp, log ve session state içinde payload kalmadığını test et.
9. Property/fuzz testlerini deterministik seed ve zaman sınırıyla çalıştır.
10. Her başarısız denemeyi ve düzeltmeyi P003 evidence paketinde sakla; clean-clone
    rerun olmadan ticket'ı kapatma.

Gerçek stylo analizi, metadata/rights iş modeli, Pinokyo corpus'u, deployment,
runtime AI, PDF/DOCX/EPUB/TEI/OCR veya lemmata.app Launch Stylometry entegrasyonu
uygulama. Bir security fixture başarısızsa P003 complete değildir.
```
