# DATA-ENDTOEND-LIT-V1 secim protokolu

**Veri kilidi kimligi:** `DATA-ENDTOEND-LIT-V1`  
**Belge surumu:** 1.0  
**Dondurma tarihi:** 2026-07-20  
**Sonuc durumu:** Henuz Delta, R `stylo`, uzaklik matrisi veya MDS sonucu uretilmedi

## 1. Amac

Bu corpus edebi yorum, yazarlik tespiti veya donemsel uslup iddiasi icin
secilmedi. Tek amaci, Delta'nin dondurulmus `delta-surface-words-v1`
hazirlama ve Classic Delta hesaplama sozlesmesinin, ayni hazirlanmis ozellik
matrisi uzerinde dogrudan R `stylo::dist.delta(z_scores, scale = FALSE)`
referansiyla sayisal olarak karsilastirilmasidir.

Bu nedenle corpus seciminde "guzel dagilim", "beklenen yazar yakinligi" veya
"iyi gorunen grafik" bir olcut degildir.

## 2. Sonuc-oncesi sinir

Aday kesfi ve bibliyografik uygunluk taramasi veri kilidinden once yapildi.
Bu taramada hicbir aday Delta'ya veya `stylo`ya verilmedi; uzaklik, MDS,
kumeleme ya da yazara gore yakinlik sonucu gorulmedi. Tarama sirasinda
incelenen ve elenen adaylar `selection_log.csv` icinde korunur.

Bu belge ve secilen alti ham dosyanin SHA-256 degerleri kilitlendikten sonra:

1. eser listesi sonuclara gore degistirilemez;
2. temizleme kurallari sessizce degistirilemez;
3. bir dosya teknik uygunluk kontrolunu gecemezse yerine baska eser konmaz;
4. bir degisiklik gerekirse yeni veri kilidi ve gerekceli protokol alt surumu
   olusturulur;
5. basarisiz, eksik veya `not_enough_features` durumlari silinmez.

## 3. Dahil etme olcutleri

Bir aday ancak asagidaki kosullarin tamamini saglarsa secilebilir:

1. Project Gutenberg resmi kaydinda dil `Italian` / `it` olmalidir.
2. Kayit bir ceviri olmamali; cevirmen alani bulunmamalidir.
3. Tek bir tanimli yazar tarafindan yazilmis ozgun Italyanca duzyazi olmalidir.
4. Tam bir bagimsiz eser ya da tek yazarli yayimlanmis duzyazi cildi olmalidir.
5. Ayni yazardan corpus'a yalniz bir belge alinmalidir.
6. Resmi UTF-8 duz metin indirmesi ve sabit Project Gutenberg eBook numarasi
   bulunmalidir.
7. Project Gutenberg kaydi eseri ABD'de kamu mali olarak gostermelidir.
8. Yazar olum tarihi, 2026 itibariyla AB'deki genel yasam + 70 yil suresinin
   disinda kalmalidir.
9. Temiz edebi govde en az 25.000 `delta-surface-words-v1` tokeni icermelidir.
10. Alti belgenin birlikte olusturdugu aday havuz, on kayitli 100, 300, 500 ve
    1000 MFW duzeylerini desteklemelidir.

Dokuzuncu ve onuncu maddeler yalniz corpus uygunluk kontroludur. Bu kontrolde
uzaklik veya edebi sonuc hesaplanmaz.

## 4. Dislama olcutleri

Asagidaki durumlardan biri adayi dislar:

- Italyanca disindaki dil veya ceviri;
- yalniz sesli kitap dizini, eksik metin ya da kisa parca;
- cok yazarli derleme;
- ayni yazarin corpus'ta zaten temsil edilmesi;
- belirsiz eser/tanik veya belirsiz erisim-hak kaydi;
- yinelenen edisyon ya da ayni metnin ikinci kopyasi;
- bozuk UTF-8, corpus icinde BOM veya yeniden uretilemeyen kaynak;
- 25.000 token altinda temiz govde;
- 1000 MFW icin yetersiz ozellik cesitliligi;
- sonuc goruldukten sonra yapilan secim onerisi.

## 5. Dondurulan eser listesi

| Belge kimligi | Yazar | Eser | Project Gutenberg |
|---|---|---|---:|
| `DOC-MANZONI-PROMESSI-PG45334` | Alessandro Manzoni | *I promessi sposi* | 45334 |
| `DOC-COLLODI-PINOCCHIO-PG52484` | Carlo Collodi | *Le avventure di Pinocchio* | 52484 |
| `DOC-DEAMICIS-CARROZZA-PG62400` | Edmondo De Amicis | *La Carrozza di tutti* | 62400 |
| `DOC-DELEDDA-DIVORZIO-PG43226` | Grazia Deledda | *Dopo il divorzio* | 43226 |
| `DOC-FOGAZZARO-MISTERO-PG22504` | Antonio Fogazzaro | *Il mistero del poeta* | 22504 |
| `DOC-PIRANDELLO-CAVALLO-PG56775` | Luigi Pirandello | *Un cavallo nella luna: Novelle* | 56775 |

Secim bir yazar-bir belge ilkesini uygular. Roman, cocuk romani, ani-gozlem
duzyazisi ve novelle cildi arasindaki tur farki bu katmanda bir hata degildir;
bu corpus edebi karsilastirma degil, sayisal motor parity'si icindir. Tur veya
donem yorumu bu sonuclardan uretilmeyecektir.

## 6. Temizleme siniri

Temizleme en dusuk mudahale ilkesini uygular:

1. Project Gutenberg ustbilgisi, lisans sonlugu ve kitap sonu dizin/notlari
   edebi govdenin disinda birakilir.
2. Her eser icin baslangic ve bitis isaretleri `source_register.csv` icinde
   birebir kaydedilir.
3. Edebi govde icindeki bolum basliklari, bolum ozetleri ve yazar tarafindan
   kurulmus cerceve metin korunur.
4. Acikca gorsel betimi olan `[Illustrazione: ...]` bloklari cikarilir.
5. Yazim, noktalama, tarihsel imla, aksan ve diyalekt bicimleri modernlestirilmez.
6. Satir sonlari LF'ye ve metin Unicode NFC'ye donusturulur; bu teknik
   donusumler gunlukte kaydedilir.
7. Temiz metin tek LF ile biter.

Ham indirme dosyalari degistirilmeden `raw/` altinda korunur. Temiz metinler
ayri `clean/` dosyalaridir; iki katmanin hash'leri birbirinin yerine gecmez.

## 7. On kayitli yeterlik karari

Corpus ancak su kosullarda `locked` olabilir:

- alti ham dosyanin tamami resmi kayitla ve SHA-256 ile eslesir;
- alti temiz dosya UTF-8, NFC ve tek-LF sozlesmesini gecer;
- her temiz belge en az 25.000 token icerir;
- temiz belgeler arasinda byte-duzeyinde tam kopya yoktur;
- corpus genelinde en az 1000 benzersiz token vardir;
- toplu sikliga gore ilk 1000 ozelligin her birinde alti belge uzerinde sonlu
  ve pozitif orneklem standart sapmasi vardir;
- exact token 10-gram ortusme raporu uretilmistir;
- hicbir Delta, `stylo`, uzaklik, MDS veya kumeleme sonucu uretilmemistir.

Bu karar "Delta testi gecti" anlamina gelmez. Yalnizca deney girdisinin
sonuclardan once sabitlendigini ve on kayitli dort MFW kosusunu teknik olarak
destekledigini gosterir.

## 8. Hak siniri

Project Gutenberg her alti kaydi da "Public domain in the USA" olarak
etiketler. Yazar olum yillari 1873-1936 arasindadir. AB Telif Suresi
Direktifi 2006/116/EC Madde 1(1), genel koruma suresini yazar yasami + 70 yil
olarak tanimlar. Paket bu iki kaydi birlikte saklar; buna ragmen hukuki gorus
sunmaz.

Ham Project Gutenberg dosyalari kendi ustbilgi/lisans metinleriyle korunur.
Temiz metinlerin kamuya yeniden dagitimi, yayim aninda hedef ulke ve barindirma
ortami icin yeniden kontrol edilir. Delta'nin canli servisi bu corpus'u kalici
olarak kullanici verisi gibi saklamak veya uretim servisine gommek zorunda
degildir.
