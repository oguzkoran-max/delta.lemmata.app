# Delta Session Handoff

**Güncellendi:** 2026-07-10  
**Aşama:** P000 kapandı; P001 başlamaya hazır  
**Kod durumu:** Ürün kodu yazılmadı  
**Aktif ticket:** Henüz açılmadı  
**Sıradaki tek ana iş:** P001 repository, lock, metadata ve provenance scaffold

## Önce Oku

1. START_HERE.md
2. Bu dosya
3. docs/development/roadmap-P001-P015.md içindeki yalnız P001 bölümü
4. decisions/ADR-0003-fair-provenance-and-memory.md
5. decisions/ADR-0008-scholarly-vibe-coding.md
6. docs/research/claim-evidence-matrix.md içindeki CE-12, CE-18, CE-19 ve CE-20
7. docs/security/threat-model.md içindeki SEC-16, RP-08 ve RP-09

## Son Oturumda Kesinleşenler

- P000 kapanmıştır; kapsam, yöntem, claim, threat, environment ve P001-P015 acceptance sözleşmeleri yazılmıştır.
- Uzun başlangıç belgelerinin ajan bütçesini tüketmesini önlemek için START_HERE.md ve aktif-ticket okuma yönlendirmesi eklenmiştir.
- CE-11 ve CE-12 geçmeden başlıkta veya güçlü ana claim'de `reproducible` kullanılmaz; `reproducibility-oriented` kullanılır.
- Kısa ürün vaadi, desteklenen akışlarda `without first learning or writing R or Python code` biçimindedir; bu structural no-code vaadi genel usability, ease, learnability veya yöntem bilgisine ihtiyaç olmadığı iddiası değildir.
- Oğuz formal Python yazılım geliştirme uzmanlığı olmadan Delta'yı Claude ve Codex ile geliştirmektedir. Bu scholar-led, evidence-gated yöntem `scholarly vibe coding` olarak ADR-0008'de tanımlanmıştır.
- P001'den itibaren HumanDecision kaydı, Oğuz'un yöntem/claim/acceptance sahipliğini AI implementasyon yardımından ayıracaktır.
- Delta tool-first bir DBB projesi ve makalesidir.
- v0.1 arayüzü lda.lemmata.app gibi yalnız İngilizcedir; mimari sonraki Türkçe ve İtalyanca yerelleştirmeye hazır tutulur.
- Makalenin ana tezi, no-code erişimin tek başına yöntemsel yeterlilik sağlamadığı ve Delta'nın corpus confounds, parameter sensitivity, interpretive limits ile reproducibility öğelerini zorunlu çıktı haline getirdiğidir.
- Kullanıcı English-only v0.1 arayüzünü ve makale tezini 2026-07-10 tarihinde açıkça onayladı.
- Katılımcılı usability study yapılmayacak; Oğuz geliştirecek, Barış structured expert walkthrough ve acceptance test yapacak.
- Barış'ın testi bağımsız kullanıcı çalışması sayılmayacak; kolaylık, genel usability veya öğreticilik iddiası kurulmayacak.
- Oğuz birinci ve sorumlu, Barış ikinci yazar olacaktır; Hakan yalnız benchmark ve istatistiksel doğrulama sahipliği gerçekleşirse üçüncü yazar adayıdır.
- Hedef Umanistica Digitale gönderimi Şubat 2027'dir; kanıt kapıları eksikse tarih ötelenir.
- Pinokyo yazar tespiti değil, public ve FAIR-oriented Style Over Time worked example'ıdır.
- Demo sorusu Pinokyo'nun Collodi kariyerinde kararlı bir pivot gibi görünüp görünmediğini, tür, hedef kitle, edisyon ve parametre denetimleriyle sınar.
- Style Over Time v0.1'de birinci sınıf analiz amacıdır.
- PhiloEditor aynı eserin redaksiyonlarını karşılaştırır; Delta bağımsız eserlerin global stilometrik konumunu ve kanıt kararlılığını inceler.
- Delta diff, alignment, varyant anotasyonu, iki sütunlu edisyon karşılaştırması veya kritik edisyon üretmez.
- Pinokyo sürüm karşılaştırması v0.1 demosundan çıkarılmıştır.
- Demo corpus'u audience-controlled core ve exploratory broad career panorama olarak ikiye ayrılır.
- Haklar underlying work, edition, scan, transcription, markup, annotation ve derived output düzeyinde ayrı kaydedilir.
- Public Research Mode job başına en fazla 24 sürümlü hücre; tam 192 hücre kontrollü publication batch'tir.
- Stability confidence değildir; eşikler benchmark calibration ile belirlenip locked test ve Pinokyo öncesinde dondurulur.
- De Amicis ayrı bir sonraki edebiyat uygulaması olarak korunur.
- Runtime AI v0.1'de yoktur.
- stylo ana motordur; Delta uncertainty ve reproducibility katmanıdır.
- FAIR iddiası kanıt dosyaları ve machine-readable metadata ile desteklenir.
- PromptEvent, Ticket, HumanDecision, Commit, ADR ve Run ayrı kaydedilir.
- Bağlam hafızası sıkıştırma öncesine bırakılmaz; karar anında güncellenir.
- Eski 1.815 satırlık Claude briefi docs/archive/ altına taşınmıştır.

## P001 Bloklayıcıları

Kullanıcı kararı gerektiren bloklayıcı yoktur. Repo topolojisi P001'de mevcut Git yapısı incelendikten sonra ADR-0009 ile karara bağlanır. Tercih, Delta'yı ayrı ve yayımlanabilir repository olarak tutmaktır; akademik asistan kök deposundaki kullanıcı değişikliklerine dokunulmaz.

Sonraki ticket'larda acceptance işi olarak izlenecekler:

- Aday Collodi eserlerinin item-level source, edition ve rights audit'i
- `research-grid-v1` kesin hücre tanımının benchmark öncesi dondurulması
- Token, segment, CPU, RAM ve timeout değerlerinin yük testiyle belirlenmesi
- Stability eşiklerinin calibration ve locked test üzerinde doğrulanması

## Sonraki Ajan İçin Talimat

`prompts/P001-start.md` içindeki şablonu gerçek oturum mesajı olarak kullan. Önce P001 Ticket, PromptEvent ve HumanDecision kayıtlarını aç; ardından yalnız roadmap'teki P001 kapsamını uygula. P002 UI veya analiz özelliği yazma. Gerçek test ve kanıt olmadan P001'i tamamlandı sayma. Daha önce onaylanmış ürün kararlarını yeniden sorma.

## Çalışma Ağacı Notu

Akademik asistan kök çalışma ağacında Delta dışı çok sayıda kullanıcı değişikliği vardır. Bunlara dokunma veya geri alma. Delta dosyaları şu anda ana repo içinde yeni ve izlenmeyen bir klasör olabilir; ayrı Git repo kararı P001'de verilecektir.

## P000 Kanıt Paketi

- docs/development/p000-closure.md
- docs/development/roadmap-P001-P015.md
- docs/development/supported-environments.md
- docs/research/claim-evidence-matrix.md
- docs/security/threat-model.md
- docs/methodology/pinocchio-diachronic-worked-example.md
- memory/checkpoints/2026-07-10-p000-closed.md
- memory/checkpoints/2026-07-10-scholarly-vibe-coding.md
