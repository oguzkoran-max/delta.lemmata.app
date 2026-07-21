# Degerlendirme surumu dondurma kaydi

**Freeze ID:** `FREEZE-LIT-PARITY-20260720-01`  
**Tarih:** 2026-07-20T10:12:30Z  
**Durum:** Surum donduruldu; parity kosulari baslatilmadi

## Birbirinden bagimsiz kanit halkalari

1. Canli `https://delta.lemmata.app/` arayuzu erisilebilir build adinda tam
   kaynak commit'ini gostermistir:
   `31e09782ba07e6709cbdcca48bc9db22e6c49723`.
2. GitHub Actions CI kosusu `29696014941` ayni commit icin `verify` ve
   `container` islerini basariyla tamamlamistir.
3. Immutable image yayin kosusu `29696211566`, ayni commit etiketini su digest'e
   baglamistir:
   `ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa`.
4. Canli Streamlit health ucu ayni gozlem turunda `ok` donmustur.

## Bilinen gozlem siniri

Canli sunucunun SSH kapisi kimlik dogrulamadan once banner zaman asimina
ugramistir. Bu nedenle canli konteynerde dogrudan `docker inspect` readback'i
alinamamistir. Sunucuda degisiklik yapilmamistir. Dondurma, canli arayuzdeki tam
build kimligi ile o commit'e ait tek basarili immutable image yayin kaydinin
eslestirilmesine dayanir. Bu sinir makalede veya ek malzemede gizlenmeyecektir.

## Degistirmeme kurali

- Dondurulan commit, image digest, corpus veya parity yapilandirmasi sessizce
  degistirilemez.
- Kosu oncesi canli build yeniden okunur. Fark varsa kosu durdurulur ve yeni
  run/attempt kaydi acilir.
- Bu kayit yalniz surum kimligini dondurur. Delta ile dogrudan R `stylo`
  sonuclarinin eslestigini, bir MFW ayarinin daha iyi oldugunu veya herhangi bir
  edebi bulguyu kanitlamaz.
