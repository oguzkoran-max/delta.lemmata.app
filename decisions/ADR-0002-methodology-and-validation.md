# ADR-0002: Canonical Methodology and Validation

**Durum:** Kabul edildi  
**Tarih:** 2026-07-10

## Bağlam

Eski briefte Guided Mode MFW listesi, unknown calibration ve stability ölçütleri birbiriyle çelişiyordu. Tek bir dendrogram veya stylo parity testi ürünün bilimsel olarak doğrulandığını göstermeye yetmez.

## Karar

- Classic Burrows Delta ana metrik
- Surface forms, lowercase, punctuation/numbers removed
- Stopwords retained, lemmatization off
- Guided MFW: 100/300/500/1000
- Unknown ve holdout tüm feature calibration'dan çıkarılır
- Segmentler eser düzeyinde gruplanır; bağımsız örnek sayılmaz
- Stability, group agreement yanında rank, margin, co-placement ve distance-family consistency kullanır
- Eder's ve Cosine Delta yalnız sensitivity kontrolleridir
- Style Over Time ayrı v0.1 araştırma amacıdır; bağımsız eser, tarih metadata'sı ve chronology-confound audit gerektirir
- Yalnız ilk ve son eserle zaman etkisi iddiası kurulmaz
- Stability etiketi confidence değildir; eşikler calibration benchmark üzerinde belirlenip locked test ve worked example öncesinde dondurulur
- Kararlılık skoru benchmark doğruluğuyla beklenen yönde ilişki göstermiyorsa nitel stability etiketleri kaldırılır

## Validasyon Katmanları

1. R stylo hesaplama parity
2. Birden fazla bağımsız eserli known-author benchmark
3. Çok yazarlı ve eser düzeyinde ayrılmış diachronic benchmark
4. Non-candidate negative control
5. Kilitli environment repeatability
6. Bağımsız clean-room rerun
7. Barış Yücesan ile structured expert walkthrough ve predefined acceptance test; genel usability kanıtı değildir

## Sonuçlar

micro_delta_gold yalnız numerical equivalence kanıtıdır. Pinokyo yalnız worked example'dır ve eşik kalibrasyonuna girmez. Ürün validasyonu bütün kanıt katmanlarının ortak sonucudur.
