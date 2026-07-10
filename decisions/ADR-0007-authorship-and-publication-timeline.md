# ADR-0007: Authorship Roles and Publication Timeline

**Durum:** Kabul edildi  
**Tarih:** 2026-07-10

## Bağlam

P000 kapanmadan önce makale liderliği, expert test sorumluluğu, olası computational validation katkısı ve hedef gönderim takvimi netleştirilmeliydi.

## Karar

- Oğuz Koran birinci ve sorumlu yazardır.
- Oğuz Koran conceptualization, methodology, scholar-led software development, corpus curation, investigation, visualization, human acceptance ve original draft sorumluluklarını üstlenir.
- Barış Yücesan ikinci yazardır; validation, structured expert walkthrough, Pinokyo corpus değerlendirmesi, yöntem eleştirisi ve writing-review sorumluluklarını üstlenir.
- Hakan Cangır ancak benchmark ve istatistiksel doğrulamanın sahipliğini fiilen üstlenirse üçüncü yazar olarak değerlendirilir.
- Nihai yazar listesi gönderim öncesinde gerçekleşen CRediT katkılarına karşı yeniden doğrulanır.
- Claude ve Codex yazar değildir; ADR-0008 scholarly vibe coding süreci yöntem, provenance ve disclosure bölümünde açıklanır.

## Hedef Takvim

- Temmuz-Ağustos 2026: Uygulama geliştirme
- Eylül-Ekim 2026: Benchmark, Collodi corpus'u ve hak denetimi
- Kasım 2026: Barış Yücesan expert walkthrough ve acceptance test
- Aralık 2026: FAIR-oriented release ve clean-room rerun
- Ocak 2027: Makale yazımı, iç denetim ve profesyonel İngilizce son okuma
- Şubat 2027: Umanistica Digitale gönderimi

## Koruyucu Koşullar

- Takvim kanıt kalitesini düşürmek için kullanılmaz.
- Rights gate, benchmark, clean-room rerun veya acceptance test tamamlanmazsa gönderim tarihi ötelenir.
- Yalnız isim veya genel destek yazarlık için yeterli değildir.
- Barış'ın walkthrough'u bağımsız usability study diye sunulmaz.

## Sonuç

P000 karar soruları ve kapanış artifact'ları tamamlanmıştır. Sıradaki aşama P001 repository, lock, metadata ve provenance scaffold'udur.
