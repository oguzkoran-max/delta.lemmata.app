# Delta Memory Protocol

## Neden Sadece Sıkıştırma Öncesi Kayıt Yetmez?

Bağlam sıkıştırması önceden güvenilir bir uyarı vermeyebilir. Model sıkıştırma anında bir özet alabilir, fakat bu özet bütün gerekçeleri, reddedilen yolları ve kullanıcı nüanslarını korumayabilir.

Bu nedenle hafıza event-driven tutulur. Karar çıktığı anda yazılır.

## Üç Operasyonel Katman

1. PROJECT_MEMORY.md: uzun vadeli bağlam ve karar geçmişi
2. SESSION_HANDOFF.md: mevcut durum, açık bloklayıcılar ve sıradaki iş
3. checkpoints/: yalnız kritik dönüm noktalarının tarihli özeti

Bunların üzerinde DEVELOPMENT_CONTRACT.md kanonik sözleşme, decisions/ ise karar gerekçesi olarak durur.

## Checkpoint Açma Ölçütü

Yeni checkpoint yalnız şu durumlarda açılır:

- Ürün veya makale yönü değişti
- Ana metodoloji donduruldu
- P000, MVP, beta veya release kapısı geçildi
- Büyük denetim sonucu proje planı değişti
- Uzun oturum veya ajan devri nedeniyle ayrıntılı devam notu gerekiyor

Günlük küçük değişiklikler checkpoint açmaz. Handoff güncellenir.

## Saklanacak İçerik

- Kullanıcı kararı
- Kararın gerekçesi
- Değerlendirilen ve reddedilen alternatifler
- Kanıt veya kaynak
- Etkilenen dosya, ticket, ADR ve run
- Açık sorular
- En fazla üç anahtar kullanıcı alıntısı

## Saklanmayacak İçerik

- Tam sohbet transkripti
- Tekrarlanan ara açıklamalar
- Ham chain-of-thought
- Şifre, token, kişisel veya telifli corpus içeriği
- Doğrulanmamış iddiayı karar gibi gösteren özet

## Sıkıştırma Sonrası Kurtarma

Yeni bağlamda önce adaptör, sözleşme, proje hafızası ve handoff okunur. Ardından yalnız aktif ticket ve ilgili ADR açılır. Bu okuma sırası, konuşmanın en başını modele yeniden yüklemek yerine kararların doğru ve daha kısa temsilini sağlar.

