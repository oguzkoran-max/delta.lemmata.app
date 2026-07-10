# Checkpoint: PhiloEditor Boundary and Diachronic Pinocchio Pivot

**Tarih:** 2026-07-10  
**Aşama:** P000  
**Kod:** Ürün kodu başlamadı

## Tetikleyici

Kullanıcı Delta'nın PhiloEditor'dan mutlaka belirgin biçimde ayrılmasını ve Pinokyo örneğinin yazar tespiti yerine Collodi'nin zaman içindeki üslupsal farklılıklarını göstermesini istedi.

## Araştırma Bulgusu

PhiloEditor aynı eserin farklı redaksiyonlarını word-based diff ile karşılaştırır, yerel varyantları gösterir, sınıflandırır ve anotasyon veya kişisel edisyon üretimine izin verir. Pinokyo için 1881-1883 tefrikası ile 1983 Castellani Pollidori kritik edisyonunu sunar.

Collodi'nin yalnız ilk ve son eserini karşılaştırmak zaman, tür, hedef kitle, uyarlama ve edisyon etkilerini ayıramaz. Literal ilk eser drama olduğu için erken ve geç düzyazıyı doğrudan karşılaştırmak özellikle yanıltıcı olabilir.

## Alınan Karar

- Pinokyo known-answer unknown authorship demosu iptal edildi.
- İki Pinokyo sürümünü karşılaştıran opsiyonel akış iptal edildi.
- Style Over Time v0.1'de ayrı analiz amacı oldu.
- Worked example adı `Collodi Before and After Pinocchio: Is the Apparent Stylistic Shift Robust?` olarak belirlendi.
- Audience-controlled core ile exploratory broad career panorama ayrı run'lar olacak.
- PhiloEditor görev sınırı diff, alignment, varyant anotasyonu, iki sütunlu edisyon ve kritik edisyon yasağıyla donduruldu.
- Public Research Mode en fazla 24 hücre, full publication batch en fazla 192 hücre olacak.
- Stability confidence değil parameter stability olacak; eşikler benchmark calibration ile belirlenecek.
- Haklar asset düzeyinde kaydedilecek; belirsiz haklı ham metin public pakete girmeyecek.

## O Anda Açık Olan, Sonradan Kapanan P000 Soruları

Bu checkpoint anında üç konu açıktı. Aynı gün sonraki kararlarla kapandı:

1. UI yalnız İngilizce; yerelleştirme mimarisi sonraki sürüme hazır.
2. Katılımcılı kullanıcı çalışması yok; Barış structured expert walkthrough yapacak.
3. Oğuz birinci/sorumlu, Barış ikinci yazar; hedef Umanistica Digitale Şubat 2027.

## Kanonik Dosyalar

- DEVELOPMENT_CONTRACT.md
- PROJECT_MEMORY.md
- SESSION_HANDOFF.md
- decisions/ADR-0002-methodology-and-validation.md
- decisions/ADR-0003-fair-provenance-and-memory.md
- decisions/ADR-0004-pinocchio-worked-example.md
- decisions/ADR-0005-public-research-and-stability.md
- docs/methodology/pinocchio-diachronic-worked-example.md

## Kullanıcı Alıntısı

> "PhiloEditor mutlaka ama mutlaka farklı olmalı. Farkı ortaya koymalıyız."
