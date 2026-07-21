# DATA-ENDTOEND-LIT-V1 motor parity corpus'u

Bu klasor, Delta'nin dondurulmus Classic Delta hesaplama sozlesmesini dogrudan
R `stylo` referansiyla karsilastirmak icin kullanilacak cok eserli Italyanca
corpus'u hazirlar.

## Bilimsel sinir

Bu paket bir edebi bulgu degildir. Yazar tespiti, uslup gelisimi, donem farki
veya eserler arasi anlamli yakinlik iddiasinda bulunmaz. Amaci iki hesaplama
yolunun ayni hazirlanmis matriste ayni sayisal sonucu verip vermedigini
sinamaktir.

## Klasorler

| Yol | Islev |
|---|---|
| `selection_protocol.md` | Sonuc-oncesi dahil etme, dislama ve degistirmeme kurallari |
| `selection_log.csv` | Incelenen kabul ve red adaylarinin tam gunlugu |
| `source/` | Resmi Project Gutenberg HTML/RDF kayitlari ve HTTP basliklari |
| `raw/` | Degistirilmemis UTF-8 Project Gutenberg indirmeleri |
| `clean/` | Belgelenmis dis sinirlarla uretilen edebi govdeler |
| `rights/` | Kamu mali ve yeniden dagitim siniri |
| `config/` | Dondurulmus insan-okur ve makine-okur MFW, profil, ortam ve parity kabul kurali |
| `scripts/` | Deterministik corpus olusturma, paket denetimi ve sonuc-koru preflight kodu |
| `mfw-0100/` ... `mfw-1000/` | Daha sonra gercek kosularin kaniti; su anda sonuc yok |

## Yeniden olusturma

Ham dosyalar ve kaynak kayitlari yerindeyken:

```bash
python3 scripts/build_corpus.py
python3 scripts/verify_package.py
```

Ilk komut temiz metinleri ve uygunluk kanitlarini yeniden uretir. Ikinci komut
hash, Unicode, satir sayisi, iliskisel alanlar ve "sonuc henuz yok" sinirini
denetler.

Kesin R/stylo sayisal cekirdek on kontrolu ayrica su iki dosyayla kaydedilir:

- `scripts/smoke_stylo_dist_delta.R`
- `scripts/preflight_release.py`

Tarih, makine ve tam paket yolunu iceren uretilmis kanit
`config/preflight_report.json` dosyasindadir. Bu rapor 22/22 kontrolu gecmis,
ancak denetlenebilir kesin referans calistirma yolu bulunmadigi icin durumu
`blocked_exact_reference_execution_path` olarak kaydetmistir. Bu durum bir
parity sonucu degildir.

## Insan tarafindan okunacak temel dosyalar

1. `selection_protocol.md`
2. `rights/rights_record.md`
3. `cleaning_log.md`
4. `metadata.csv`
5. `corpus_qc.json`
6. `overlap_report.csv`
7. `package_manifest.csv`
8. `config/release_freeze.md`
9. `config/preflight_report.md`

`corpus_qc.json` icindeki `eligible_for_preregistered_mfw_grid: true`, yalniz
corpus'un 100/300/500/1000 MFW kosularina teknik olarak yetecegi anlamina
gelir. Delta'nin veya `stylo` parity testinin gectigi anlamina gelmez.
