# P002 Start Prompt Template

**Kayıt türü:** Human-reviewed handoff template
**PromptEvent değildir:** Bu dosya henüz Claude veya Codex'e gönderilmiş native
mesaj kanıtı sayılmaz. Gönderildiğinde gerçek içerik, zaman, araç, model ve hash
ayrı PromptEvent olarak kaydedilir.

```text
P002: English-only workbench shell

START_HERE.md ve SESSION_HANDOFF.md dosyalarını oku. Ardından roadmap'teki yalnız
P002 bölümünü, ADR-0001 ve ADR-0008'i, claim CE-01/18/20 ile threat SEC-14/EPI-13
kayıtlarını incele. P001 ticket ve acceptance raporundan temel ortamın geçtiğini
doğrula. Daha önce onaylanmış ürün kararlarını yeniden sorma.

Önce P002 Ticket ve bu gerçek isteğe ait PromptEvent kaydını aç. Sonra:
1. Pazarlama landing page'i yerine doğrudan English-only Streamlit workbench shell kur.
2. Text Proximity, Group Comparison ve Style Over Time amaçlarını ilk ekranda göster.
3. Guided ve Research mode ayrımını kur; henüz çalışmayan işlevleri açıkça disabled tut.
4. Bütün kullanıcı metnini merkezi English string registry'de tut; TR/IT çeviri ekleme.
5. Empty, loading, error, cancel ve complete state component sözleşmesini oluştur.
6. Version/build bilgisi veren, secret veya system path sızdırmayan health/readiness ekle.
7. Runtime AI, analytics, login ve permanent storage dependency/config denetimini koru.
8. Lemmata ailesiyle akraba fakat stilometri workbench'ine özgü sakin, yoğun ve erişilebilir bir arayüz tasarla.
9. Desktop ve mobile Playwright screenshot, keyboard accessibility, copy denylist ve ağ kapalı smoke testlerini çalıştır.
10. Kanıtları provenance/evidence/P002 altında sakla; claim/threat/handoff durumunu gerçek sonuca göre güncelle.

Ingestion, gerçek stylo hesaplaması, corpus metadata, Pinokyo verisi veya deployment
uygulama. Ekranda confidence, find the author, easy for everyone, no knowledge
needed ya da kanıtsız reproducible dili kullanma. P002 gate'lerinden biri geçmezse
ticket'ı complete işaretleme.
```
