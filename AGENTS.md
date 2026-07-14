# Delta Agent Instructions

Bu dizinde çalışan tüm Codex ve diğer ajanlar önce şu minimum paketi okur:

1. START_HERE.md
2. SESSION_HANDOFF.md
3. docs/development/roadmap-P001-P015.md içindeki aktif, yoksa sıradaki planlanan ticket bölümü
4. Aktif veya sıradaki ticket'ta işaretlenen claim, threat ve ADR kayıtları

DEVELOPMENT_CONTRACT.md ve PROJECT_MEMORY.md; mimari/yöntem kararı, belge çelişkisi, P000/P015 kapanışı, release veya START_HERE.md içinde sayılan özel durumlarda tamamen okunur. Bu yönlendirme bağlam tasarrufu içindir; kanonik sözleşmenin otoritesini değiştirmez.

docs/archive/ altındaki belgeler tarihsel bağlamdır. Kanonik talimat değildir.

## Çalışma Kuralları

- P001-P006 kapanmıştır. P007 aktif Ticket'tır. `HD-20260714-0001` yöntem
  paketini kabul etmiş ve ADR-0014 Accepted olmuştur; P007'yi schema-first ve
  tests-first uygula, kabul edilen sınırları yeni insan kararı olmadan değiştirme.
- `HD-20260714-0002` ve ADR-0015, bütün minimum kapılar geçerse 2026-07-17
  Public-alpha hedefini kabul eder. Hız için privacy, admission, real-result,
  explanation, resource, isolation, rollback veya Lemmata smoke kapısını atlama.
- P006 fixture-local worker parity, retained Linux package, scientific handoff,
  exact-commit Linux CI ve remote clean-clone kapılarını geçti. Bu kanıtı
  preprocessing, benchmark, public workflow, FAIR export, Pinokyo veya production
  iddiasına genişletme.
- P003/P004 kanıtını production retention, gerçek `stylo` veya host isolation kanıtı gibi genişletme.
- P005'te application-managed deletion ile secure erase, snapshot, swap, backup veya production isolation iddiasını karıştırma.
- Aynı anda yalnız bir aktif P-ticket ve tek güncel handoff tut.
- Kullanıcının onayladığı soruları yeniden sorma.
- Runtime AI, dış API, analytics, login veya kalıcı proje saklama ekleme.
- lda.lemmata.app koduna, environment'ına, portuna veya verisine dokunma.
- R styloyu gizleme veya kendi Delta formülünü kanonik motor gibi sunma.
- P006 process exit code 0 değerini tek başına scientific success kabul etme;
  strict output ve semantic validation guardian ACK'den önce tamamlanmalıdır.
- Unknown metni MFW, culling, mean, standard deviation veya feature selection'a katma.
- Kesin yazarlık, nedensellik veya pure style dili üretme.
- Pinokyo'yu makalenin ana araştırma nesnesine dönüştürme; worked example olarak tut.
- Pinokyo'yu authorship demo'ya veya iki sürümlü PhiloEditor benzeri karşılaştırmaya geri döndürme.
- Diff, alignment, varyant anotasyonu, iki sütunlu edisyon karşılaştırması veya kritik edisyon işlevi ekleme.
- Style Over Time sonucunu yaşlanma, olgunlaşma veya nedensel gelişim gibi sunma.
- FAIR'i kalite sertifikası veya open ile eş anlamlı sunma.
- Scholarly vibe coding'i “AI uzmanlığın yerini alır” veya “her araştırmacı güvenilir yazılım üretebilir” diye genelleme.
- Kullanıcı değişikliklerini geri alma.

## Hafıza Protokolü

Bağlam sıkıştırmasını bekleme. Şu olaylardan hemen sonra belgeleri güncelle:

- Kullanıcı yeni karar onayladı
- Bir ADR kabul edildi veya değişti
- P-ticket tamamlandı veya engellendi
- Test, hakem veya güvenlik bulgusu sözleşmeyi etkiledi
- Oturum devrediliyor veya kapanıyor

Güncellenecekler:

- Kalıcı karar veya gerekçe: PROJECT_MEMORY.md
- Güncel durum ve sıradaki iş: SESSION_HANDOFF.md
- Mimari/yöntem kararı: ilgili ADR
- Kritik dönüm noktası: memory/checkpoints/YYYY-MM-DD-*.md

Tam transkript kopyalama. Karar, gerekçe, alternatif, kanıt, sonuç ve en fazla üç anahtar kullanıcı alıntısı kaydet.

## Provenance

P001'den itibaren her gerçek LLM mesajı PromptEvent, geliştirme işi Ticket, insan-owned yöntem/claim/acceptance kararı HumanDecision, Git değişikliği Commit, karar ADR, bilimsel koşum Run olarak ayrı kimlik alır. Retrospektif kayıtları native veya exact diye etiketleme.

## Her Ticket Sonunda

- Değişen dosyaları listele.
- Gerçek test komutlarını ve sonuçlarını kaydet.
- Claim-evidence bağlantısını güncelle.
- SESSION_HANDOFF.md dosyasını güncelle.
- Gerekirse PROJECT_MEMORY.md ve ADR'yi güncelle.
