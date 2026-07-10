# ADR-0005: Public Research Grid and Parameter Stability

**Durum:** Kabul edildi  
**Tarih:** 2026-07-10

## Bağlam

Research Mode'un tam aday gridi 4 MFW, 4 culling, 4 segment ve 3 distance düzeyiyle en çok 192 hücre üretir. Delta, lda.lemmata.app ile aynı VPS üzerinde izole servis olarak çalışacaktır. Tam gridin her public kullanıcıya sınırsız açılması ortak sunucu kaynaklarını ve hizmet sürekliliğini riske atar.

Eski taslakta stability için yüzde 75 ve yüzde 50 gibi kanıtsız eşikler önerilmişti. Aynı sonucun farklı parametrelerde tekrar etmesi doğruluk veya confidence anlamına gelmez.

## Karar

- Public v0.1 job'u en fazla 24 analiz hücresi çalıştırır.
- Public hücreler sonuç görüldükten sonra seçilmez; sürümlenmiş, dengeli ve hashlenmiş `research-grid-v1` preset'i kullanılır.
- Tam 192 hücre yalnız kontrollü publication batch veya yönetici koşumunda çalıştırılır.
- Hücre sayısına ek olarak dosya, token, segment, CPU, RAM, timeout ve eşzamanlı job sınırları yük testiyle belirlenir.
- Global queue aynı anda bir çalışan ve en fazla üç bekleyen R job ile sınırlıdır.
- Arayüz confidence değil parameter stability raporlar.
- Stability eşikleri calibration benchmark üzerinde belirlenir ve locked test ile Pinokyo worked example görülmeden önce dondurulur.
- Stability skoru benchmark doğruluğuyla beklenen yönde ilişki göstermiyorsa Stable, Partially stable ve Unstable etiketleri kaldırılır; ham bileşenler gösterilir.

## Stability Bileşenleri

- Modal nearest group veya modal work-level placement
- Rank agreement
- Distance-family içinde normalize edilmiş top-two margin
- Cluster co-placement
- Geçerli feature sayısı
- Distance-family direction consistency
- Style Over Time için leave-one-work-out etkisi

## Sonuçlar

Public kullanıcı yöntemsel duyarlılığı görebilir, fakat ortak VPS tam publication gridini herkese aynı anda sunmak zorunda kalmaz. Makale public 24 hücrelik kullanıcı akışı ile kontrollü tam validation batch'ini ayrı kanıt nesneleri olarak raporlar.

24 sayısı tek başına altyapı kapasitesi iddiası değildir. Sayısal corpus ve runtime sınırları P014 öncesinde yük testiyle dondurulur ve deployment manifestine yazılır.
