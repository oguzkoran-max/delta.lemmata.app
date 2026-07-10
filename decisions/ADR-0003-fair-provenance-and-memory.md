# ADR-0003: FAIR, Provenance, and Persistent Memory

**Durum:** Kabul edildi  
**Tarih:** 2026-07-10

## Bağlam

Lemmata prompt arşivi değerli bir şeffaflık katmanı sundu, fakat Git geçmişi prompt dosyalarının bir bölümünün oturum günlüklerinden sonradan aktarıldığını gösterdi. Prompt sayısı, ticket sayısı, commit sayısı ve gerçek mesaj sayısı birbirine karışabiliyor. Bağlam sıkıştırması da konuşma içindeki kararların yalnız modele emanet edilmesini riskli kılıyor.

## Karar

- PromptEvent, Ticket, HumanDecision, Commit, ADR ve Run ayrı kimliklerdir.
- Kayıt modu native, transcribed veya reconstructed olarak açıkça belirtilir.
- Prompt arşivi FAIR'in kendisi değil, provenance katmanıdır.
- FAIR-oriented paket CodeMeta, CFF, RO-Crate, rights, source manifest, lockfiles ve checksums içerir.
- Hak kaydı underlying work, source edition, scan, transcription, markup, annotation, normalized text ve derived output katmanlarını ayrı tutar.
- `unknown` veya `permission_required` durumundaki ham varlık public demo, export veya release içine girmez.
- Full model response yayımlanmak zorunda değildir; hash ve redaksiyon kabul edilir.
- Bağlam hafızası sıkıştırma öncesine bırakılmaz, karar anında güncellenir.
- Scholarly vibe coding sürecinde alan uzmanının yöntem, claim ve acceptance sahipliği AI implementasyon yardımından HumanDecision kayıtlarıyla ayrılır.
- Formal Python uzmanlığı olmadan geliştirme öz-konumlanması açıkça beyan edilir; bundan genellenebilir ease veya uzmanlığın gereksizliği sonucu çıkarılmaz.

## Hafıza Katmanları

- Kanonik sözleşme: DEVELOPMENT_CONTRACT.md
- Kalıcı karar hafızası: PROJECT_MEMORY.md
- Güncel devir paneli: SESSION_HANDOFF.md
- Karar gerekçesi: decisions/
- Dönüm noktası özeti: memory/checkpoints/
- Değişiklik izi: Git

## Sonuçlar

Her ajan aynı dosyaları okuyarak başlayabilir. Full transcript arşivleme zorunlu değildir. Kararların gerekçesi, alternatifleri, insan sahipliği ve kanıtı kaybolmaz. Ayrıntılı scholarly vibe coding kararı ADR-0008'dedir.
