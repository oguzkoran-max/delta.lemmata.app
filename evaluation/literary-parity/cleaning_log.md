# Deterministik temizleme gunlugu

**Veri:** `DATA-ENDTOEND-LIT-V1`  
**Profil:** `delta-surface-words-v1`  
**Sonuc siniri:** Uzaklik, MDS, Delta ve R stylo sonucu uretilmedi.

| Belge | Kaynak satirlari | CRLF | NFC degisti | Gorsel blogu | Token |
|---|---:|---:|---|---:|---:|
| DOC-MANZONI-PROMESSI-PG45334 | 2179-25366 | 25761 | False | 39 | 222415 |
| DOC-COLLODI-PINOCCHIO-PG52484 | 70-6626 | 7140 | False | 79 | 40688 |
| DOC-DEAMICIS-CARROZZA-PG62400 | 65-11286 | 11828 | False | 0 | 115142 |
| DOC-DELEDDA-DIVORZIO-PG43226 | 65-7756 | 8124 | False | 0 | 58179 |
| DOC-FOGAZZARO-MISTERO-PG22504 | 103-7534 | 7922 | False | 0 | 62214 |
| DOC-PIRANDELLO-CAVALLO-PG56775 | 80-4569 | 4958 | False | 0 | 36743 |

Uygulanan islemler: kayitli govde sinirini alma; CRLF/CR satir sonlarini LF'ye cevirme; Unicode NFC; acik `[Illustrazione: ...]` bloklarini cikarma; tek son LF yazma.

Uygulanmayan islemler: imla modernlestirme, stopword cikarma, lemmatization, stemming, konuya gore secim, uzaklik veya grafik sonucuna gore belge degistirme.

On kayitli MFW izgara uygunlugu: `true`.
Bu deger motor parity testinin gectigi anlamina gelmez.
