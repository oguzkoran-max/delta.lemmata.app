# P001 Start Prompt Template

**Kayıt türü:** Human-reviewed handoff template  
**PromptEvent değildir:** Bu dosya henüz Claude veya Codex'e gönderilmiş native mesaj kanıtı sayılmaz. Gönderildiğinde gerçek içerik, zaman, araç, model ve hash ayrı PromptEvent olarak kaydedilir.

```text
P001: Repository, locks, metadata, and provenance scaffold

START_HERE.md ve SESSION_HANDOFF.md dosyalarını oku. Ardından docs/development/roadmap-P001-P015.md içindeki yalnız P001 bölümünü incele. P001'in işaretlediği ADR-0003 ve ADR-0008'i, claim CE-12/18/19/20 ile threat SEC-16/RP-08/RP-09 kayıtlarını oku.

Önce mevcut klasör ve Git topolojisini yalnız incele. Akademik asistan kök deposundaki kullanıcı değişikliklerini geri alma, taşıma veya temizleme. Delta için ayrı ve FAIR-açısından yayımlanabilir repository topolojisini değerlendir; sonucu ADR-0009 olarak kaydet. Gerekmedikçe P001 dışındaki ürün kararlarını yeniden sorma.

Sonra:
1. P001 ticket kaydını aç ve kısa uygulama planını yaz.
2. Python/R lock, minimal package/test yapısı, version/metadata dosyaları, PromptEvent/Ticket/HumanDecision/Run provenance şemaları ve CI/security scaffold'unu yalnız roadmap kapsamına göre uygula.
3. Gerçek format, lint, type, test, schema, lock, secret ve path taramalarını çalıştır.
4. Kanıtları provenance/evidence/P001 altında, test komutları ve sürümlerle sakla.
5. Human-decision ledger içinde Oğuz'un yöntem/claim/acceptance sahipliği ile AI implementasyon yardımını ayrı kaydet.
6. Claim-evidence ve threat kayıtlarında yalnız gerçekten doğrulanan durumları güncelle.
7. SESSION_HANDOFF.md dosyasını P001 sonucu ve sıradaki tek işle güncelle.

P002 UI veya analiz özelliği yazma. Bir acceptance testi geçmezse P001'i tamamlandı diye işaretleme. Yalnız uygulamayı gerçekten durduran bir belirsizlik varsa bana tek, açık soru sor; aksi halde proaktif ilerle.
```
