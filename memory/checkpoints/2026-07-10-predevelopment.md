# Checkpoint: Predevelopment Decisions and Audit

**Tarih:** 2026-07-10  
**Kayıt türü:** Retrospektif, konuşma ve denetim sentezi  
**Kapsam:** Delta fikrinin olgunlaştırılması, Lemmata denetimi, FAIR, Umanistica Digitale, Pinokyo ve hafıza mimarisi

## Nereden Başlandı?

Kullanıcı genel kullanıcıya hitap eden, edebiyat ve DBB alanında somut bir tool ve makale üretmek istedi. Farklı fikirler elendikten sonra stilometri seçildi ve delta.lemmata.app adı benimsendi. Ana vaat, R veya Python öğrenmeden stilometri yapabilmek ve sonucun ne anlama geldiğini öğrenmekti.

AI'nin runtime'a eklenmesi maliyet, gizlilik ve telif nedeniyle ertelendi. Tool klasik ve tekrar üretilebilir yöntemlerle çalışacak; AI yalnız geliştirme sürecinde kullanılabilecek.

## Lemmata'dan Alınan Ders

Lemmata sitesi, DSH proof'u, GitHub kodu ve P001-P041 prompt arşivi incelendi. Editör, yöntem, FAIR, mimari ve adversarial rollerinde beş bağımsız ajan çalıştı.

Güçlü yönler:

- Scholar-led geliştirme
- Açık kod, test, DOI ve sürümleme
- Başarısızlıkları ve AI kullanımını açıklama
- Real corpus validation
- Environment ve analiz çıktısı export'u

Tespit edilen iyileştirme alanları:

- Public prompt kayıtları ile gerçek prompt event sayısı aynı değildi
- Bazı kayıtlar session loglarından sonradan aktarılmıştı
- Full response yerine result summary bulunmasına rağmen repo dili daha genişti
- Zenodo ve Data Availability arasında artifact açığı vardı
- App, CFF, package ve release version drift'i vardı
- Dependency locking, retention kanıtı ve live-link kontrolü güçlendirilmeliydi

Bu bulgular Delta'nın provenance-by-design ve machine-readable FAIR sistemini doğurdu.

## Bilimsel Yöntem Kararı

Delta'nın asıl yeniliği tek dendrogram üretmek değil, sonucun parametreler değiştiğinde korunup korunmadığını göstermektir.

Kanonik hat:

- R stylo
- Classic Burrows Delta
- Surface forms
- Stopwords retained
- MFW 100/300/500/1000
- Unknown calibration dışında
- Multi-axis sensitivity
- Open-set ve claim guardrails

Parity, known-author benchmark, negative control, locked rerun ve structured expert walkthrough birbirinden ayrı kanıt katmanları olarak tanımlandı. Sonraki ADR-0006 kararıyla katılımcılı kullanıcı çalışması v0.1'den çıkarıldı; genel usability iddiası kurulmayacaktır.

## Makale Yönü

Bir aşamada De Amicis seyahat yazıları ana vaka olarak düşünüldü. Dört eserde ülke, kitap, tarih ve konu birbirine karıştığı için coğrafya etkisi iddiasının savunulamayacağı anlaşıldı.

Pinokyo sürümleri daha kontrollü bir edebî araştırma imkânı sundu, fakat kullanıcı makalenin Pinokyo araştırmasına dönüşmesini istemedi. Son karar:

- Makale Delta tool'u hakkındadır.
- Pinokyo public worked example'dır.
- De Amicis bağımsız, sonraki edebiyat/TÜBİTAK çıktısıdır.
- AI-assisted development ana katkı değildir.

## Hafıza Kararı

Kullanıcı bağlam sıkıştırmalarında hiçbir kararın unutulmamasını istedi. Yalnız sıkıştırma öncesi Markdown kaydı güvenilir bulunmadı, çünkü sıkıştırma önceden haber vermeyebilir.

Kabul edilen yapı:

- Agent-nötr DEVELOPMENT_CONTRACT.md
- Kalıcı PROJECT_MEMORY.md
- Rolling SESSION_HANDOFF.md
- Karar ADR'leri
- Kritik checkpoint'ler
- Git geçmişi
- Claude ve Codex için ince adaptörler

Bu checkpoint tam transkript değildir. Projenin bugünkü konumuna nasıl ulaştığını yeniden kurmak için gerekli karar zincirini saklar.

## Sonraki Adım

P000'de kalan yedi bloklayıcı karar kullanıcıyla kapatılacak. Ardından repo, lockfiles, test altyapısı ve provenance scaffold'u P001 ile başlayacak.
