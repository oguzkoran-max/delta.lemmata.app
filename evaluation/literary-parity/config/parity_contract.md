# Direct R stylo parity sozlesmesi

**Veri:** `DATA-ENDTOEND-LIT-V1`  
**Protokol:** `PROTO-EVAL-DELTA-1.1`  
**Durum:** Corpus, yapilandirma ve degerlendirme surumu donduruldu. Ilk
sonuc-koru on kontrol 22/22 teknik denetimi gecti ve o tarihte kesin referans
calistirma yolunu blokeli kaydetti. Bu tarihsel rapor korunur. Sonradan kurulan
GitHub Actions yurutme yolu, ayri `execution_contract.json` ve
`execution_preflight.json` kayitlariyla sonuc gorulmeden denetlenir. Deney
kosusu henuz baslatilmadi.

## Dondurulan degerlendirme surumu

| Alan | Dondurulan deger |
|---|---|
| Git commit | `31e09782ba07e6709cbdcca48bc9db22e6c49723` |
| OCI image | `ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa` |
| Basarili CI | `29696014941` |
| Immutable image yayini | `29696211566` |
| Canli build gozlemi | `https://delta.lemmata.app/`, 2026-07-20T10:12:30Z |

Canli arayuz tam Git commit'ini erisilebilir adinda gostermis, ayni commit icin
tek basarili immutable image yayin kosusu yukaridaki OCI digest'ini uretmistir.
SSH yonetim kapisi gozlem sirasinda banner zaman asimina ugradigi icin canli
konteynerde dogrudan `docker inspect` readback'i alinamamistir. Bu sinir
`release_freeze.md` dosyasinda acikca kayitlidir.

## On kontrol sonucu

`preflight_report.json` ve insan-okur `preflight_report.md`, corpus, protokol,
MFW grid'i, release kimligi, dort kosu satiri, bos sonuc hash'leri, bos outcome
tablosu, R 4.5.2 ve tam `stylo 0.7.71` sayisal Delta cekirdegini 22 denetimle
dogrulamistir. Sayisal cekirdek, ayni paket nesne veritabanindan arayuz
bagimliligindan ayrilarak bagimsiz Manhattan/formul sonucu ile sifir farkla
karsilastirilmistir.

Bu kontrol parity sonucu degildir. macOS'ta normal `stylo` namespace'inin
ekledigi GUI yigini XQuartz gerektirmektedir; ayrica donmus OCI image'i yerelde
calistiracak bir konteyner motoru ve canli sunucuya dogrudan SSH readback'i
yoktur. Deney, dogrudan R referansi ile donmus Delta surumunu denetlenebilir
sekilde calistiracak yol kurulmadan baslatilmaz.

## Sabit kosullar

| Alan | Dondurulan deger |
|---|---|
| Corpus rolu | known-only engine-parity corpus |
| Analiz birimi | whole text; alti bagimsiz yazar belgesi |
| Hazirlama profili | `delta-surface-words-v1` |
| MFW | 100, 300, 500, 1000; tumu raporlanir |
| Culling | 0% |
| Uzaklik | Classic Delta |
| Seed | 20260713 |
| R | 4.5.2 |
| stylo | 0.7.71 |
| Locale | C.UTF-8; sayisal locale C |
| Saat dilimi | UTC |
| Referans | `stylo::dist.delta(z_scores, scale = FALSE)` |

## Karsilastirma siniri

Delta ve dogrudan R `stylo` ayni sirali belge etiketlerini, ayni sirali
ozellikleri ve ayni hazirlanmis z-skoru matrisini kullanir. Ham metinleri iki
farkli varsayilan boru hattina verip sonuclari karsilastirmak yasaktir; bu,
hazirlama farki ile motor farkini birbirine karistirir.

## Basari kurali

Her MFW kosusu ayri degerlendirilir:

- sirali belge etiketleri birebir ayni;
- sirali ozellik listesi birebir ayni;
- uzaklik matrisi hucre farki en fazla `1e-6`;
- yapisal/simetri farki en fazla `1e-12`;
- diagonal sifir;
- es uzaklik gruplari birebir ayni.

Es uzaklik grubu, bir satirdaki en kucuk sifir-disi uzakliga mutlak farki
`1e-12` veya daha az olan butun belgelerden olusur. Isci ya da referans
ciktisinda sonlu olmayan tek bir sayi, tamamlanmamis tek bir fit/cell veya
fatal artifact bulunmasi otomatik basarisizliktir. Fatal artifact varsa proses
cikis kodunun sifir olmasi sonucu degistirmez. Hazirlanmis z-skoru matrisleri
arasindaki en buyuk mutlak fark `1e-12` sinirini asamaz.

Bir MFW kosusu gecmezse diger kosu onun yerine gecmez. `500 MFW` yalniz
arayuzdeki ilk gosterim tercihidir; en iyi ayar sayilmaz.

Kosudan hemen once canli arayuzdeki build kimligi tekrar okunur. Dondurulan
commit'ten farkliysa kosu baslatilmaz; mevcut satir sessizce degistirilmez ve
yeni bir run/attempt kaydi acilir.

## Corpus uygunluk kontrolunun yapmayacagi seyler

`build_corpus.py` yalniz token sayisi, benzersiz ozellik, orneklem standart
sapmasi, Unicode, hash, yinelenen dosya ve exact 10-gram ortusmesini kontrol
eder. Asagidakileri hesaplamaz:

- Classic Delta uzakligi;
- R `stylo` sonucu;
- MDS koordinati;
- kumeleme;
- yazar veya donem yakinligi;
- "en iyi" MFW secimi.
