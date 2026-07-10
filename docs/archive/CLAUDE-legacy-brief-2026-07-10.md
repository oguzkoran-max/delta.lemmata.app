# Delta Workbench: Claude Code Başlangıç Briefi

Bu dosya `delta.lemmata.app` projesini Claude Code ile geliştirmek için hazırlanmış ana yol haritasıdır. Claude bu dosyayı okuyunca doğrudan kod yazmaya başlamamalı; önce aşağıdaki soru turunu yürütmeli, kullanıcının kararlarını almalı, sonra MVP'yi küçük ve doğrulanabilir adımlarla geliştirmelidir.

## Bağlayıcı Karar Hiyerarşisi ve P000 Kuralı

Bu dosya birkaç tasarım turunun birikimidir. Bu nedenle Claude Code, dosyanın eski bölümlerindeki seçenekleri son karar gibi okumamalıdır.

Çelişki varsa karar sırası şudur:

1. Bu bölümdeki P000 ve kapsam kilidi
2. Üçüncü Denetim Geçişi
3. İkinci Tasarım Geçişi
4. Proje Kimliği ve Projenin Ana Kararı
5. Eski soru turu ve ilk geliştirme notları

Kanonik v0.1 sözleşmesi:

- AI yok, dış API yok, analytics yok.
- Login yok, kalıcı kullanıcı projesi yok.
- Girdi biçimleri yalnız `.txt`, `.zip`, metadata `.csv`.
- PDF, DOCX, EPUB, TEI, OCR yok.
- R `stylo` ana motor; Python/Streamlit yalnız arayüz, iş akışı ve export katmanı.
- Classic Burrows Delta ana metrik.
- Surface word forms kullanılır; lemmatization kapalıdır.
- Stopword removal kapalıdır; Delta, özel bir function-word listesi değil, stopword'leri koruyan MFW yaklaşımıdır.
- Guided Mode her zaman `100 / 300 / 500 / 1000` MFW setini dener.
- 1000 MFW küçük corpusta mümkün değilse sistem bunu açıkça "not enough features" olarak raporlar.
- Unknown text, mümkünse referans corpus istatistiklerini belirlerken dışarıda tutulur; raporda `unknown_in_feature_calibration` alanı açık yazılır.
- Toponym-clean, maskeleme değil, `custom_exclusions.txt` ile feature listesinden dışlama olarak uygulanır.
- De Amicis hattı v0.1'de genel bir Style Over Geography modülü değil, dar ve küratörlü demonstrator'dır.
- Style Over Time v0.1'de genel özellik değil, metadata uyarısı ve v2 araştırma hattıdır.
- Varsayılan export `FAIR Package, no raw texts`.
- Demo corpus hak kontrolü bitmeden public demo'ya ham metin eklenmez.
- `lda.lemmata.app` uygulamasına, env'ine, systemd unit'ine, veri klasörlerine ve portuna dokunulmaz.
- Upload güvenliği, job queue, resource limits, temp cleanup, validation ve FAIR export MVP sonrası değil, MVP kapısıdır.

Claude Code ilk mesajda mutlaka P000 ile başlamalıdır. P000'de kod yazılmaz, scaffold başlatılmaz.

P000 çıktısı şunları içermelidir:

1. v0.1 kapsam kilidi
2. çelişen kararların çözümü
3. kanonik metodoloji protokolü
4. upload güvenliği planı
5. job queue ve resource limit planı
6. aynı Hetzner sunucuda `lda.lemmata.app` izolasyon planı
7. FAIR-lite export kanonik dosya listesi
8. P001-P015 uygulanabilir sıra
9. en fazla 7 bloklayıcı soru

Kullanıcı P000 sözleşmesini onaylamadan kod yazmaya başlama.

## Proje Kimliği

**Ad:** Delta  
**Alan adı:** `delta.lemmata.app`  
**Ürün ailesi:** Lemmata  
**İlk sürüm ilkesi:** AI yok, dış API yok, local/server-side klasik stilometri  
**Ana hedef:** R, Python veya `stylo` bilmeyen DBB/edebiyat araştırmacısına öğretici, güvenli ve tekrar üretilebilir stilometri deneyi yaptırmak.

Kısa ürün cümlesi:

> R, Python veya stylo öğrenmeden stilometrik deney kur, sonucu gör, ayarların sonucu nasıl değiştirdiğini anla ve raporunu indir.

Akademik konumlandırma:

> Delta is not a replacement for stylo. It is a reproducibility and interpretation layer for literary stylometry.

Delta'nın amacı yeni bir stilometri algoritması icat etmek değildir. Amaç, Burrows's Delta ve yakın stilometrik işlemleri web üzerinde öğretilebilir, denetlenebilir, parametre duyarlılığı görünür ve tekrar üretilebilir hale getirmektir.

## Projenin Ana Kararı

İlk sürümde yapay zeka kullanılmayacak.

Neden:

- AI API maliyeti belirsizdir.
- Kullanıcı metinlerinin dış API'ye gönderilmesi veri/telif/gizlilik riski yaratır.
- Stilometri hesabı zaten klasik ve tekrar üretilebilir yöntemlerle yapılmalıdır.
- Tool önce bağımsız, ücretsiz ve güvenilir çalışmalıdır.

Gelecek sürümde AI ancak opsiyonel "Method Coach" olarak düşünülebilir. İlk sürümde bunun için kod yazma, sadece mimaride ileride eklenebilirlik notu bırak.

## Neden Bu Proje Var?

Stilometri araçları güçlüdür ama yeni kullanıcı için üç sorun çıkarır:

1. Kurulum ve teknik eşik: R, Python, `stylo`, paket kurulumu, dosya biçimi.
2. Yorum riski: Tek dendrogramı kesin yazarlık kanıtı sanma.
3. Tekrar üretilebilirlik riski: Hangi ayarla, hangi korpusla, hangi preprocessing ile sonucun üretildiğinin kaybolması.

Delta bu üç sorunu çözmelidir:

- Analizi çalıştırır.
- Kullanıcıya ne yaptığını öğretir.
- Sonucun ne kadar sağlam veya kırılgan olduğunu gösterir.
- Bütün ayarları ve çıktıları export eder.

## Rakipler ve Fark

Bu proje "ilk web tabanlı stilometri aracı" değildir. Böyle iddia etme.

Mutlaka bilinmesi gereken mevcut araçlar:

- `stylo` R paketi: alanın merkez aracı, GUI ve CLI desteği vardır.
- WebSty: web tabanlı stilometri sistemi olarak daha önce geliştirilmiştir.
- JGAAP: non-expert kullanıcıya authorship attribution yaptıran Java tabanlı araçtır.
- Programming Historian dersleri: Burrows's Delta'yı öğretici biçimde anlatır.
- Voyant: genel metin analizi ortamıdır, doğrudan authorship attribution aracı değildir.

Delta'nın farkı şu olmalı:

- `stylo`yu gizlemez, motor olarak veya referans olarak kabul eder.
- "Tek sonuç" vermez, parametre duyarlılığını gösterir.
- Corpus sağlık kontrolü yapar.
- Dendrogram/PCA yorumuna epistemik fren koyar.
- Her analiz için reproducibility paketi üretir.
- Yeni başlayanlar için Guided Mode sunar, uzmanlar için Advanced Mode bırakır.

## Claude İçin İlk Talimat

Kodu yazmaya başlamadan önce kullanıcıya soru turu yap.

Kurallar:

- Soruları 5'erli bloklar halinde sor.
- Her soruda 2-4 seçenek ver.
- Her soruda kendi önerini belirt.
- Kullanıcı bir bloğu cevaplamadan sonraki bloğa geçme.
- Kullanıcı "varsayılanları uygula" derse aşağıdaki önerilen varsayılanları kullan.
- Sorular bitmeden dosya yapısı, framework veya UI konusunda kesin uygulama başlatma.

## Soru Turu

### Blok 1: Ürün ve Dil Kararları

**1. Arayüz dili ne olsun?**  
Önerim: İngilizce ana arayüz, Türkçe yardım metinleri opsiyonel.

A. Tamamen İngilizce  
B. Tamamen Türkçe  
C. İngilizce arayüz + Türkçe açıklama modu  
D. TR/EN dil anahtarı

Gerekçe: Akademik görünürlük için İngilizce daha iyi; Oğuz'un kullanım ve ders bağlamı için Türkçe açıklama modu değerli.

**2. İlk hedef kullanıcı kim?**  
Önerim: Kod bilmeyen DBB/edebiyat araştırmacısı.

A. Kod bilmeyen DBB/edebiyat araştırmacısı  
B. Lisans/YL öğrencisi  
C. Forensic linguistics uzmanı  
D. Genel okur

**3. Ana vaat nasıl yazılsın?**  
Önerim: "Run stylometric experiments without learning R or Python."

A. "Find the author of a text."  
B. "Explore stylistic similarity in your corpus."  
C. "Run stylometric experiments without learning R or Python."  
D. "Teach and reproduce Burrows's Delta."

**4. İlk sürümde kaç analiz amacı olsun?**  
Önerim: Üç ana amaç + demo.

A. Yalnız yazar yakınlığı  
B. Yazar yakınlığı + grup karşılaştırması  
C. Yazar yakınlığı + grup karşılaştırması + Style Over Time  
D. C + ders/demo modu

**5. İlk sürümde "unknown text" desteği olsun mu?**  
Önerim: Evet, ama kesin yazarlık iddiası olmadan.

A. Hayır, sadece bilinen metinleri karşılaştırsın  
B. Evet, unknown metni en yakın gruplarla karşılaştırsın  
C. Evet, ama sadece Advanced Mode'da  
D. Sonraki sürüme kalsın

### Blok 2: Girdi ve Corpus Kararları

**6. İlk sürüm hangi dosya türlerini kabul etsin?**  
Önerim: `.txt`, `.zip`, metadata `.csv`.

A. Sadece `.txt`  
B. `.txt` + `.zip`  
C. `.txt` + `.zip` + metadata `.csv`  
D. PDF/DOCX/TEI dahil

**7. PDF/OCR ilk sürümde olsun mu?**  
Önerim: Hayır.

A. Hayır  
B. Evet, basit PDF text extraction  
C. Evet, OCR dahil  
D. Sonraki sürümde plugin olarak

**8. Metadata zorunlu alanları neler olsun?**  
Önerim: temel akış için `filename`, `title`, `author`, `group`, `language`, `known_status`; Style Over Time / Geography akışında `year`, `genre`, `source`, `copyright_status` ayrıca istenir.

A. Sadece filename/author  
B. filename/title/author/group  
C. filename/title/author/group/language/known_status  
D. C + year/genre/source/copyright

**9. Public demo corpus olacak mı?**  
Önerim: Evet, public-domain küçük İtalyanca demo corpus.

A. Hayır  
B. Evet, küçük İtalyanca demo corpus  
C. Evet, İtalyanca + Türkçe demo corpus  
D. Evet, kullanıcı seçilebilir birkaç demo seti

**10. Telif uyarısı nasıl olsun?**  
Önerim: Upload öncesi kısa ve net uyarı.

A. Sadece footer privacy note  
B. Upload öncesi kısa uyarı  
C. Kullanıcı checkbox ile onaylasın  
D. Public sürümde telifli metin yükleme tamamen yasak

### Blok 3: Analiz ve Varsayılanlar

**11. Stilometri motoru ne olsun?**  
Önerim: R `stylo` motoru + Python/Streamlit arayüz.

A. R `stylo` subprocess  
B. Saf Python implementasyon  
C. R `stylo` + Python fallback  
D. Önce Python, sonra `stylo` validasyonu

**12. Varsayılan MFW değerleri ne olsun?**  
Önerim: 100 / 300 / 500 / 1000 birlikte.

A. Tek değer: 500  
B. 100 / 300 / 500  
C. 100 / 300 / 500 / 1000  
D. Kullanıcı seçsin, varsayılan yok

**13. İlk sürümde hangi distance measure olsun?**  
Önerim: Classic Burrows Delta, varsa Cosine Delta ek.

A. Sadece Classic Burrows Delta  
B. Classic Burrows Delta + Cosine Delta  
C. Classic + Eder's Delta + Cosine Delta  
D. Çoklu metrik paketi

**14. Stopword kaldırma varsayılanı ne olsun?**  
Önerim: Kapalı.

A. Kapalı  
B. Açık  
C. Kullanıcıya sor  
D. Dile göre otomatik

Gerekçe: Stilometri çoğu zaman sıradan işlev kelimelerindeki kullanım alışkanlıklarını ölçer.

**15. Lemmatization ilk sürümde olsun mu?**  
Önerim: Hayır.

A. Hayır, surface word forms  
B. Evet, İtalyanca için  
C. Evet, TR/IT/EN için  
D. Advanced Mode'da deneysel olarak

### Blok 4: UX ve Öğretici Katman

**16. Ana modlar nasıl olsun?**  
Önerim: Guided Mode + Advanced Mode.

A. Sadece Guided Mode  
B. Guided Mode + Advanced Mode  
C. Wizard + Expert Panel  
D. Tek ekran, bütün ayarlar aynı yerde

**17. Sonuç ekranı önce ne göstermeli?**  
Önerim: Grafiklerden önce sonuç kartları.

A. Dendrogram  
B. PCA  
C. Sonuç kartları + uyarılar  
D. Mesafe matrisi

**18. Sağlamlık paneli MVP'de zorunlu mu?**  
Önerim: Evet, Delta'nın ayırt edici özelliği.

A. Evet  
B. Hayır, sonraki sürüme kalsın  
C. Sadece Advanced Mode'da  
D. Sadece unknown text analizinde

**19. Öğretici mikro-metin düzeyi nasıl olsun?**  
Önerim: Kısa açıklama + "Learn more" açılır alanları.

A. Minimum metin  
B. Kısa açıklamalar  
C. Kısa açıklama + Learn more  
D. Ders portalı gibi uzun açıklamalar

**20. Export formatları ne olsun?**  
Önerim: HTML rapor + ZIP reproducibility paketi.

A. Sadece CSV/PNG  
B. HTML rapor + CSV/PNG  
C. HTML rapor + ZIP reproducibility paketi  
D. DOCX/PDF dahil tam rapor

### Blok 5: Teknik ve Yayın Kararları

**21. Deployment hedefi ne olsun?**  
Önerim: Aynı Hetzner sunucuda ayrı servis.

A. Local-only  
B. Streamlit Cloud  
C. Aynı Hetzner sunucuda `delta.lemmata.app`  
D. Ayrı VPS

**22. İlk sürümde kullanıcı hesabı olacak mı?**  
Önerim: Hayır.

A. Hayır  
B. Basit şifreli beta  
C. Kullanıcı hesabı  
D. Kurumsal login

**23. Kullanıcı dosyaları saklansın mı?**  
Önerim: Hayır, işlem bitince silinsin.

A. Hayır, temp silinsin  
B. Kullanıcı isterse proje olarak saklansın  
C. Sadece metadata saklansın  
D. Beta süresince loglansın

**24. Makale hedefi ne olsun?**  
Önerim: Önce Umanistica Digitale.

A. Umanistica Digitale  
B. DSH  
C. JCLS  
D. Sadece tool, makale sonra

**25. Makalenin ana iddiası ne olsun?**  
Önerim: Parametre duyarlılığı + öğretilebilirlik + yeniden üretilebilirlik.

A. Yeni web stylometry aracı  
B. Burrows Delta'yı öğretici hale getiren web aracı  
C. Parametre duyarlılığı, yorum disiplini ve reproducibility için Delta protokolü  
D. İtalyan edebiyatında yeni authorship attribution vakası

## Varsayılan Karar Seti

Kullanıcı hızlı ilerlemek isterse şu varsayılanları uygula:

- Arayüz: İngilizce, Türkçe açıklama modu sonraya açık.
- Hedef kullanıcı: kod bilmeyen DBB/edebiyat araştırmacısı.
- AI: yok.
- Girdi: `.txt`, `.zip`, metadata `.csv`.
- PDF/OCR: yok.
- Motor: R `stylo` + `Rscript` subprocess.
- Arayüz: Streamlit.
- Varsayılan MFW: 100 / 300 / 500 / 1000.
- Varsayılan ölçü: Classic Burrows Delta.
- Stopword removal: kapalı.
- Lemmatization: yok.
- Modlar: Guided + Advanced.
- Sonuç ekranı: önce sonuç kartları, sonra grafikler.
- Sağlamlık paneli: zorunlu.
- Export: HTML rapor + ZIP reproducibility paketi.
- Deployment: `delta.lemmata.app`, aynı Hetzner, ayrı systemd servisi.

## MVP Özellikleri

### 1. Proje Başlangıcı

Kullanıcı yeni analiz başlatır.

Alanlar:

- Project name
- Corpus language
- Research aim
- Use demo corpus button

Mikro-metin:

> Delta compares writing habits, not themes. Its results are exploratory evidence, not automatic proof of authorship.

### 2. Dosya Yükleme

Desteklenen girdiler:

- Tek tek `.txt`
- `.zip` içinde `.txt`
- Metadata `.csv`

Kurallar:

- Yalnız `.txt`, `.zip`, `.csv`.
- PDF, DOCX, TEI, EPUB yok.
- ZIP içinde nested archive yok.
- Symlink, absolute path, `../` reddedilir.
- Upload limiti varsayılan 25 MB.
- ZIP açılmış toplam limit varsayılan 100 MB.

Yükleme sonrası tablo:

- filename
- word count
- status
- missing metadata?
- short text warning?

### 3. Metadata Masası

Zorunlu alanlar:

- `filename`
- `title`
- `author`
- `group`
- `language`
- `known_status`

Opsiyonel alanlar:

- `year`
- `genre`
- `period`
- `source`
- `copyright_status`
- `notes`

Metadata validasyonu:

- Her dosya metadata tablosunda bulunmalı.
- En az iki grup/yazar olmalı.
- Unknown varsa en az iki bilinen referans grubu olmalı.
- Dil karışımı uyarı vermeli.
- Tür karışımı uyarı vermeli.

### 4. Corpus Sağlık Kontrolü

Üç seviye:

**Bloklayıcı**

- En az iki karşılaştırma grubu yok.
- Bilinen metin yok.
- Metadata eşleşmesi yok.
- Hiç geçerli `.txt` yok.

**Uyarı**

- 5.000 kelimenin altında metinler var.
- Metin uzunlukları çok dengesiz.
- Dil karışık.
- Tür karışık.
- Bir grupta tek metin var.

**Bilgi**

- Stopword kaldırma kapalı, bu önerilen ayardır.
- Guided Mode varsayılanları kullanılacak.
- Unknown metinler referans corpus'a dahil edilmeyecek.

Örnek uyarı dili:

> This corpus can be analyzed, but 3 texts are shorter than 5,000 words. Treat the result as exploratory.

### 5. Guided Mode

Kullanıcı az ayar görür.

Varsayılanlar:

- Feature: most frequent words
- MFW: 100, 300, 500
- Lowercase: on
- Remove punctuation: on
- Remove numbers: on
- Stopword removal: off
- Distance: Classic Burrows Delta
- Visualizations: dendrogram, PCA, distance matrix

Guided Mode'da amaç:

- kullanıcının yanlış ayarlarla sistemi bozmasını önlemek
- sonuçları güvenli ve öğretici biçimde üretmek

### 6. Advanced Mode

Kontroller:

- MFW single value or range
- culling percentage
- minimum word threshold
- chunk size
- distance measure
- cluster method
- PCA component count
- stopword removal
- lowercase
- punctuation removal
- function words only option, ileri sürüm olabilir

Advanced uyarısı:

> These settings can substantially change the result. If you publish this analysis, keep the exported settings file.

### 7. Analiz Çıktıları

Zorunlu:

- Dendrogram
- PCA scatter plot
- Delta distance matrix
- Nearest neighbors table
- MFW robustness table
- Feature frequency table
- Result summary cards

İyi olursa:

- Stability heatmap
- KWIC for top discriminating features
- SVG export

### 8. Sonuç Kartları

Grafiklerden önce göster.

Kartlar:

1. **Nearest stylistic neighbors**
2. **Group clustering**
3. **MFW stability**
4. **Interpretation risk**
5. **Recommended next check**

Örnek kararlı sonuç:

> Unknown Text A remains closest to Author B across the tested MFW values. This suggests a stable stylistic proximity under the current settings. Report it as stylometric proximity, not definitive authorship proof.

Örnek kırılgan sonuç:

> Unknown Text A changes its nearest group across the tested MFW values. The result is unstable. Check corpus balance, text length, and genre composition before making an interpretation.

### 9. MFW Sağlamlık Paneli

Bu MVP'nin ayırt edici ekranıdır.

Tablo:

- MFW value
- nearest neighbor
- nearest group
- distance
- cluster placement
- changed from previous?

Etiketler:

- Stable
- Partially stable
- Unstable

Kurallar:

- 100/300/500/1000 koşularının en az 3'ü aynı gruba ve benzer nearest-neighbor/rank örüntüsüne işaret ediyorsa: Stable.
- 2/3 aynıysa: Partially stable.
- Hepsi farklıysa veya nearest neighbor sürekli değişiyorsa: Unstable.

Mikro-metin:

> Do not trust a single dendrogram. A stylometric result is more defensible when it remains similar across reasonable MFW settings.

### 10. Exportlar

Her analiz şu paketi üretmeli:

```text
delta_run_YYYYMMDD_HHMMSS.zip
  report/
    report.html
    methods.md
    limitations.md
  figures/
    dendrogram.png
    dendrogram.svg
    pca.png
    pca.svg
  tables/
    metadata_normalized.csv
    distance_matrix.csv
    nearest_neighbors.csv
    mfw_robustness.csv
    features_used.csv
  manifest.json
  README.txt
```

`manifest.json` alanları:

- run_id
- timestamp_utc
- app_version
- git_commit
- python_version
- r_version
- stylo_version
- input_file_hashes
- normalized_text_hashes
- settings
- preprocessing_log
- output_file_hashes
- runtime_seconds

## Teknik Mimari

Önerilen MVP mimarisi:

```text
delta.lemmata.app
  Caddy HTTPS
    -> 127.0.0.1:8502
      -> Streamlit / Python app
        -> validate uploads
        -> normalize metadata
        -> create job_config.json
        -> Rscript run_stylo.R job_config.json
        -> collect CSV/PNG/SVG outputs
        -> build report and manifest
        -> return export ZIP
```

### Motor Kararı

R `stylo` çekirdek motor olmalı.

Neden:

- Akademik meşruiyet sağlar.
- Burrows Delta ve klasik stilometri hattı için yerleşiktir.
- Hakeme "biz algoritmayı yeniden icat ettik" demeyiz.
- Delta'nın katkısı motor değil, workflow ve interpretive guardrails olur.

Python saf implementasyon yalnız test/fallback için düşünülebilir. MVP'de ana motor yapma.

### `Rscript` Neden?

`rpy2` yerine `Rscript` subprocess kullan.

Neden:

- Python ve R süreçleri ayrılır.
- R hatası Streamlit sürecini öldürmez.
- Deployment daha basit olur.
- `shell=False` ile güvenli çalıştırılabilir.

### Önerilen Dosya Yapısı

```text
delta.lemmata_app/
  CLAUDE.md
  README.md
  app.py
  pyproject.toml
  requirements.lock
  renv.lock
  .streamlit/
    config.toml
  delta/
    __init__.py
    config.py
    upload.py
    metadata.py
    validation.py
    preprocessing.py
    jobs.py
    reports.py
    manifest.py
    security.py
  r/
    run_stylo.R
  assets/
    demo_corpus/
    css/
  tests/
    fixtures/
    test_metadata.py
    test_upload_security.py
    test_manifest.py
    test_reproducibility.py
  docs/
    methodology.md
    user_guide.md
    privacy.md
    validation_plan.md
```

## Güvenlik ve Gizlilik

İlk sürümde kullanıcı dosyaları kalıcı saklanmamalı.

Kurallar:

- Her analiz için UUID job klasörü oluştur.
- Job klasörü izinleri `0700`.
- İş bitince temp dosyaları sil.
- Hata olsa bile cleanup dene.
- 2 saatten eski job klasörlerini silen cron/systemd timer planla.
- Ham metinleri loglama.
- Dosya adlarını loglarken sanitize et.
- ZIP Slip engeli koy.
- Nested archive reddet.
- Symlink reddet.
- `subprocess.run` daima `shell=False` ile çalışsın.

Privacy note kısa ve açık olmalı:

> Uploaded files are processed temporarily for the analysis and are not stored after the job is completed. Do not upload texts unless you have the right to process them.

## Deployment Notları

Mevcut Lemmata altyapısı:

- Hetzner CX23
- Caddy
- systemd
- Streamlit
- Mevcut LDA uygulaması `lda.lemmata.app`

Delta ayrı servis olmalı:

```text
lda.lemmata.app    -> 127.0.0.1:8501
delta.lemmata.app  -> 127.0.0.1:8502
```

Mevcut LDA uygulamasına dokunma.

Örnek Caddy:

```caddyfile
delta.lemmata.app {
    request_body {
        max_size 30MB
    }

    reverse_proxy 127.0.0.1:8502
}
```

Systemd hardening hedefleri:

- ayrı kullanıcı: `delta`
- `NoNewPrivileges=true`
- `PrivateTmp=true`
- `ProtectSystem=strict`
- `ProtectHome=true`
- `ReadWritePaths=/var/tmp/delta /var/lib/delta /var/log/delta`
- `MemoryMax=1500M`
- `CPUQuota=150%`

## Test Planı

### Unit Tests

- metadata CSV validation
- filename matching
- corpus health rules
- upload file type validation
- ZIP Slip protection
- manifest generation
- report generation

### Integration Tests

- fixture corpus ile analiz çalışır
- Rscript wrapper doğru output üretir
- MFW 100/300/500/1000 runs complete
- export ZIP expected files içerir
- temp cleanup çalışır

### Reproducibility Tests

- aynı corpus + aynı settings = aynı distance matrix
- manifest hashleri tutarlı
- settings JSON ile analiz tekrar çalışır

### Security Tests

- `../evil.txt` içeren ZIP reddedilir
- symlink içeren ZIP reddedilir
- nested ZIP reddedilir
- 25 MB üstü upload reddedilir
- `.py`, `.sh`, `.R` upload reddedilir

### Manual QA

- mobil/desktop görünüm
- uzun dosya adları taşmıyor
- açıklama metinleri grafiklerin üstünü kapatmıyor
- düşük veri durumunda kullanıcı anlaşılır uyarı alıyor
- hata mesajları yargılayıcı değil, öğretici

## UI Tasarım İlkeleri

- İlk ekran landing page değil, doğrudan çalışma ekranı olmalı.
- Kullanıcıyı "New Analysis" akışına sok.
- Akademik ama sade görünüm.
- Aşırı süsleme, büyük hero, pazarlama dili yok.
- Grafiklerden önce sonuç kartları.
- Her grafik yanında kısa yorum rehberi.
- Advanced ayarları varsayılan olarak gizli.
- Her kritik ayarın yanında küçük açıklama.
- "Kesin yazar budur" gibi dil yasak.

Yasak cümleler:

- "This proves the author is..."
- "The author is definitely..."
- "This text was written by..."

Kullanılacak dil:

- "This text is stylistically closest to..."
- "Under the current settings..."
- "This result is stable/unstable across MFW values..."
- "Treat this as exploratory evidence..."

## Makale Hattı

İlk makale araç tanıtımı olmamalı.

Makale sorusu:

> Burrows's Delta çıktıları parametre duyarlılığı, corpus dengesi ve yorum sınırları görünür kılındığında, stilometri kod bilmeyen edebiyat araştırmacıları için daha öğretilebilir ve tekrar üretilebilir bir yönteme dönüşür mü?

Başlık adayları:

1. *Opening Burrows' Delta: Reproducible Stylometry and Parameter Sensitivity in Italian Literary Corpora*
2. *Measuring Style, Teaching Method: A Validation Study of Burrows' Delta for Italian Literary Texts*
3. *Beyond the Stylometric Output: Teaching, Testing, and Reproducing Delta in Italian Literary Studies*

Hedef dergi:

1. Umanistica Digitale
2. DSH, ancak güçlü validasyon ve kullanıcı çalışması sonrası
3. JCLS veya DHQ, uygun özel sayı olursa

Makale katkısı:

- hesaplama doğrulaması
- parametre duyarlılığı
- öğretici workflow
- reproducibility paketi
- yorum disiplini

Tool description riskini azalt:

- Abstract'ta özellik listesi yazma.
- UI ekran görüntülerini ana katkı gibi gösterme.
- Results bölümü şu başlıklarla kurulmalı:
  - computational equivalence
  - parameter sensitivity
  - pedagogical gain
  - reproducibility audit

## Pilot Corpus Önerisi

En temiz yol kamu malı İtalyanca korpusla başlamak.

Önerilen ana pilot, proje durumuna göre iki katmanlı düşünülmelidir:

1. **Araç demosu için hızlı corpus**
   - Manzoni, De Amicis, Verga, Svevo, Pirandello gibi kamu malı veya açık lisanslı İtalyanca metinlerden küçük ve dengeli bir "Italian Classics Fingerprint" corpus'u.
   - Amaç: Kullanıcıya 2 dakika içinde Delta'nın ne yaptığını göstermek.
   - Makale ana vakası yapılmamalı; dönem, tür ve konu karışımı çok yüksektir.

2. **Makale/proje çıktısı için ana corpus**
   - TÜBİTAK 3501 kabul edilirse ana vaka De Amicis seyahat yazıları olmalıdır.
   - Öncelikli metinler: `Spagna`, `Olanda`, `Marocco`, `Costantinopoli`.
   - Mümkünse ikinci aşamada `Ricordi di Londra`, `Sull'oceano` veya diğer seyahat/prose metinleri kontrollü biçimde eklenebilir.
   - Araştırma sorusu: De Amicis'in seyahat yazılarında üslup coğrafyaya göre değişiyor mu, yoksa seyahat anlatısı içinde ölçülebilir bir stilistik süreklilik var mı?

3. **Yöntem köprüsü için ek demo**
   - Svevo üçlemesi, Lemmata LDA ile Delta arasındaki farkı göstermek için kullanılabilir.
   - Amaç: LDA'nın "metinler ne hakkında?", Delta'nın "metinler nasıl yazılmış?" sorusuna baktığını göstermek.
   - Ana makale vakası yapılmamalı; Lemmata DSH makalesine fazla yakın durabilir.

Pavese ve Sciascia:

- Ana açık veri pilotu olmasın.
- Telif ve proje çakışması riski var.
- Kapalı demo veya yöntemsel stres testi olarak düşünülebilir.

## İkinci Tasarım Geçişi: Kesinleşen Ürün Kararları

Bu bölüm, ilk brief'ten sonra yapılan ikinci ürün tartışması ve çoklu ajan değerlendirmeleriyle kesinleşen kararları içerir. Claude Code bu bölümü bağlayıcı ürün kararı olarak okumalıdır.

### 1. Ürünün Yeni Ana Konumu

Delta yalnızca "stylo web arayüzü" gibi konumlandırılmamalıdır.

Doğru konum:

> Delta is a FAIR-oriented stylometric uncertainty workbench for literary analysis.

Türkçe karşılığı:

> Delta, stilometrik sonuçların sağlamlığını, sınırlarını ve tekrar üretilebilirliğini görünür kılan öğretici bir çalışma alanıdır.

Ürün "cevap üretme" aracı değil, "kanıtı denetleme" aracıdır. Kullanıcıya tek bir dendrogram verip "sonuç budur" dememelidir. Bunun yerine şu soruları görünür kılmalıdır:

- Bu sonuç hangi MFW değerlerinde korunuyor?
- Corpus dengesi sonucu zayıflatıyor mu?
- Tür, konu, anlatıcı, edisyon veya telif durumu yorumu etkiliyor mu?
- Bu analiz yeniden üretilebilir mi?
- Export paketi hakem veya başka araştırmacı için yeterli iz bırakıyor mu?

### 2. v0.1 Sınırı

v0.1'de olmalı:

- Guided Mode
- sınırlı Advanced Mode
- `.txt`, `.zip`, metadata `.csv`
- R `stylo` backend
- Classic Burrows Delta ana metrik
- MFW sağlamlık paneli: 100, 300, 500, 1000
- dendrogram, PCA/MDS, distance matrix, nearest neighbor table
- minimal Style Over Time
- De Amicis için Style Over Geography tasarımı
- FAIR-lite export ZIP
- public demo corpus
- no login, no permanent storage

v0.1'e koyma:

- AI yorumlayıcı
- PDF, EPUB, DOCX, TEI ingestion
- Zenodo tek tık yayın
- tam RO-Crate
- bootstrap/permutation gibi ağır istatistikler
- otomatik chapter/section segmentation
- kullanıcı hesabı
- forensic-grade authorship attribution
- "kesin yazar budur" dili

### 3. Metrik Açıklama Katmanı

Her teknik kavram, arayüzde kısa açıklama ve tooltip ile sunulmalıdır.

| Kavram | Kullanıcıya açıklama | Uyarı |
|---|---|---|
| Burrows Delta | Metinlerin en sık kelimeleri kullanma alışkanlığı birbirine ne kadar yakın? | Yazar kimliğini tek başına kanıtlamaz. |
| MFW | Analize kaç sık kelime dahil edilecek? | MFW yükseldikçe sonuç otomatik olarak daha doğru olmaz. |
| z-score | Bir kelime bu metinde corpus ortalamasına göre fazla mı, az mı? | Tek kelime değil, genel örüntü yorumlanır. |
| Culling | Bir kelime kaç metinde görünürse analize alınsın? | Yüksek culling bazı ayırt edici kelimeleri dışarıda bırakabilir. |
| Dendrogram | Benzer metinleri ağaç gibi gruplayan görsel. | Tek başına nihai kanıt değildir. |
| PCA/MDS | Metin benzerliklerini iki boyutlu haritada gösterir. | Eksenlerin doğrudan edebi anlamı yoktur. |
| Distance matrix | Her metnin diğer metinlere uzaklığını tablo halinde gösterir. | Kalite veya doğruluk puanı değildir. |
| Consensus/robustness | Sonuç ayarlar değiştiğinde de korunuyor mu? | Tek grafik yerine tekrar eden örüntülere bakılmalıdır. |
| Chunking | Uzun metinleri karşılaştırılabilir parçalara bölme işlemidir. | Çok küçük parça bağlamı zayıflatır. |
| Stopword removal | "ve", "bir", "ile" gibi sık kelimeleri çıkarma işlemidir. | Stilometride bu kelimeler çoğu zaman önemlidir; varsayılan kapalı olmalıdır. |
| Lemmatization | Çekimli kelimeleri sözlük biçimine indirme işlemidir. | Üslup farklarını düzleştirebilir; varsayılan kapalı olmalıdır. |

### 4. Style Over Time

Style Over Time bir "üslup değişti mi?" düğmesi değildir. Önce corpus'un yorumlanabilir olup olmadığını kontrol eden bir analiz modudur.

Alt modlar:

- Early vs Late
- Full Career Trajectory
- Rolling Style, v2

Zorunlu metadata:

- author
- title
- publication_year
- chronological_order
- language
- original_or_translation
- edition_used
- source
- copyright_status
- genre
- narrator_person
- word_count, otomatik
- ocr_or_manual_quality
- paratext_included

Style Over Time sonuç dili:

> This mode compares stylistic distance over time. It does not prove biographical development by itself.

Kırmızı bayraklar:

- yalnız iki eser varsa: "Pairwise contrast only, not trajectory."
- tür değiştiyse: "Genre may explain the shift."
- anlatıcı değiştiyse: "Narrator position is a major confounder."
- çeviri ve özgün metin karıştıysa: "Translator style may dominate."
- OCR kalitesi düşükse: "Noise may create artificial style."
- modernize edilmiş baskı varsa: "Orthographic normalization affects features."

### 5. Style Over Geography: De Amicis Ana Vaka

TÜBİTAK 3501 kabul edilirse Delta'nın ana akademik vaka çalışması De Amicis seyahat yazıları olmalıdır.

Önerilen mod adı:

> Style Over Geography

Araştırma sorusu:

> De Amicis'in seyahat yazılarında üslup coğrafyaya göre değişiyor mu, yoksa yazarın seyahat anlatısı içinde ölçülebilir bir stilistik süreklilik var mı?

Öncelikli corpus:

- `Spagna`
- `Olanda`
- `Marocco`
- `Costantinopoli`

İkincil genişletme:

- `Ricordi di Londra`
- `Sull'oceano`
- diğer seyahat veya toplumsal gözlem metinleri, ancak tür farkı açıkça işaretlenmeli

Analiz mantığı:

1. Aynı yazar ve yakın tür ailesi korunur.
2. Coğrafya ve konu değişkenleri metadata olarak işlenir.
3. Stopword'leri koruyan MFW Delta ile topic etkisi azaltılmaya çalışılır; bu özel bir function-word listesi değildir.
4. MFW sağlamlık paneliyle sonuç tek ayara bağlı mı kontrol edilir.
5. Lemmata LDA ile gerekirse "topic" ve "style" ayrımı tartışılır.

İyi sonuç dili:

> Costantinopoli, De Amicis'in seyahat corpus'u içinde belirli MFW ayarlarında Marocco'ya daha yakın bir stil profili göstermektedir; ancak bu yakınlık coğrafi konu, yer adları ve anlatı nesnesiyle birlikte yorumlanmalıdır.

Yasak sonuç dili:

- "De Amicis İstanbul'da tamamen farklı bir üslup geliştirmiştir."
- "Coğrafya üslubu kanıtlanabilir biçimde değiştirmiştir."
- "Bu sonuç yalnızca yazarın psikolojik durumunu gösterir."

### 6. FAIR-lite Export Package

v0.1 hedefi tam RO-Crate değil, FAIR-lite deposit-ready ZIP olmalıdır.

Varsayılan export:

```text
delta-lemmata-fair-export-YYYYMMDD-HHMM.zip
  README.md
  methods.md
  limitations.md
  rerun_instructions.md
  RIGHTS.md
  CITATION.cff
  metadata.json
  manifest-sha256.json
  checksums.sha256
  parameters.json
  processing_log.json
  corpus_health.json
  environment.json
  data_availability.md
  data/
    DATA-SOURCES.csv
    document_inventory.csv
    feature_matrix.csv
  results/
    delta_distances.csv
    nearest_neighbors.csv
    summary.json
    mfw_robustness.csv
  figures/
    main_visualization.png
```

Kullanıcıya üç export seçeneği sun:

1. Results
   - sadece CSV + grafik
2. FAIR Package
   - varsayılan önerilen seçenek
   - ham metin yok
   - metadata, parametre, feature matrix, sonuçlar, checksum, ortam bilgisi var
3. Full Research Object
   - v2 veya Advanced
   - ham/temiz metinler, RO-Crate metadata, citation dosyası ve yeniden çalıştırma script'i eklenebilir

Varsayılan:

> FAIR Package, no raw texts.

Telif notu:

> FAIR açık veri demek değildir. Telifli metinlerde metadata ve parametreler paylaşılabilir, metin paylaşılmayabilir.

### 7. Demo Stratejisi

İlk ekranda kullanıcıya corpus seçtirmek yerine üç büyük demo butonu sun:

1. **Quick Demo: Italian Classics Fingerprint**
   - Manzoni, De Amicis, Verga, Svevo, Pirandello gibi yazarlardan küçük dengeli parçalar.
   - Amaç: hızlı etki ve kullanıcıyı alıştırma.
   - Makale ana vakası değildir.

2. **Research Demo: De Amicis Travel Style**
   - `Spagna`, `Olanda`, `Marocco`, `Costantinopoli`.
   - Amaç: Style Over Geography modunu göstermek.
   - TÜBİTAK 3501 ve Umanistica Digitale hattı için ana adaydır.

3. **Method Demo: Svevo LDA vs Delta Bridge**
   - Lemmata LDA ile Delta'nın farkını gösterir.
   - LDA: metinler ne hakkında?
   - Delta: metinler nasıl yazılmış?

Yedek akademik vakalar:

- Manzoni: Style Over Revision, `Fermo e Lucia` ve `I promessi sposi`
- Verga: Verismo'ya geçiş, `Tutte le novelle`
- Pirandello: anlatıcı, kimlik ve stil
- Svevo: modernist anlatı ve LDA/Delta yöntembilim köprüsü

### 8. Hakem İtirazlarına Karşı Ürün Savunması

Beklenen itiraz:

> Bu sadece stylo'nun web arayüzü mü?

Cevap:

> Delta yeni bir Delta algoritması önermez. Katkısı, Burrows Delta koşusunu geçici bir görselden çıkarıp parametreleri, corpus parmak izlerini, yazılım sürümlerini, MFW sağlamlık tanılarını ve FAIR-lite export paketini içeren denetlenebilir bir araştırma nesnesine dönüştürmesidir.

Beklenen itiraz:

> WebSty zaten web stilometri yaptı.

Cevap:

> WebSty teknik erişim eşiğini düşürüyordu. Delta, daha sonraki akademik problemi hedefler: sonuçların belirsizliği, parametre duyarlılığı, provenance ve yeniden kullanım.

Beklenen itiraz:

> CollateX ve Versus gibi araçlarla farkı ne?

Cevap:

> CollateX ve Versus textual alignment, variant comparison ve traceability alanındadır. Delta'nın alanı stylometric distance under uncertainty'dir. Aynı metni yan yana hizalamaz; stilometrik uzaklık sonuçlarının hangi koşullarda yorumlanabilir olduğunu denetler.

Sitede kesinlikle kullanılmayacak iddialar:

- First web-based stylometry tool.
- A web version of stylo.
- Proves authorship.
- Most accurate Delta tool.
- Replaces stylo, CollateX, Versus or WebSty.
- Forensic-grade authorship attribution.
- Objective result.
- Reproducible by default, eğer hash ve environment kaydı yoksa.

## Üçüncü Denetim Geçişi: Eksikler ve Sertleştirme Kararları

Bu bölüm, üçüncü çoklu ajan denetimi sonucunda eklenen risk azaltma ve kalite kararlarını içerir. Claude Code bu bölümü "ürünü mükemmelleştirme" değil, "ürünü şişirmeden sağlamlaştırma" listesi olarak okumalıdır.

Ana karar:

> Delta v0.1, genel bir stilometri evreni değil; kontrollü, öğretici, yeniden üretilebilir Burrows Delta workbench'i olacaktır.

Kısa ürün formülü:

> No-code Burrows Delta + robustness check + FAIR-lite export + De Amicis case study.

### 1. Kapsam Freni

v0.1'de ana ürün şu dört parçadan oluşur:

1. Guided Burrows Delta analizi
2. MFW robustness check
3. FAIR-lite export
4. De Amicis Style Over Geography demonstrator

Style Over Time ve Style Over Geography, v0.1'de genel ve tam modül olarak büyütülmemelidir. Bunlar:

- demo
- makale vakası
- metodolojik stres testi

olarak kullanılmalıdır.

v0.1'e ekleme:

- full GIS map
- TEI import
- saved projects
- user accounts
- automatic close-reading generator
- AI interpretation
- full report/PDF generator
- bootstrap/permutation UI
- full Rolling Delta module

Bu özellikler v2 veya makale sonrası geliştirme olarak bırakılmalıdır.

### 2. Validasyon Rejimi

Delta'nın eksik parçası hesaplama değil, sonucun ne zaman yorumlanabilir sayılacağını belirleyen validasyon rejimidir.

v0.1 için minimum validasyon:

1. **Stylo parity test**
   - Küçük fixture corpus R `stylo` ile ve Delta arayüzüyle çalıştırılır.
   - Feature list, distance matrix ve temel çıktıların uyumu kontrol edilir.
   - Eşleşme yoksa ürün "stylo-compatible" değil, "stylo-inspired" dili kullanır.

2. **Known-author sanity check**
   - Farklı yazarlardan dengeli küçük corpus ile nearest-neighbor testi yapılır.
   - Sistem bilinen yazarları makul biçimde ayıramıyorsa güçlü edebi yorum kurulmaz.

3. **MFW robustness check**
   - Her Guided analiz 100, 300, 500, 1000 MFW değerleriyle koşulur.
   - Ana yorum en az 3/4 MFW düzeyinde benzer örüntü varsa yapılır.

4. **Negative control**
   - Rastgele veya beklenmeyen karşılaştırma ile sistemin her durumda anlamlı küme üretip üretmediği kontrol edilir.
   - Her koşulda güçlü sonuç üreten sistem güvenilmez sayılır.

5. **Chunking sensitivity**
   - Uzun metinlerde 2.000 ve 5.000 token seçenekleri karşılaştırılır.
   - v0.1'de bu kontrol otomatik olmak zorunda değildir; ama mimaride ve raporda yer almalıdır.

Site yorum freni:

> Corpus health uyarısı veya düşük MFW robustness varsa sonuç keşif amaçlıdır, yayın düzeyi kanıt sayılmaz.

### 3. De Amicis İçin Topic-Style Kontrolü

De Amicis seyahat yazılarında en büyük metodolojik risk, coğrafi ve tematik sözcüklerin stil sinyali gibi görünmesidir.

Özellikle `Costantinopoli`, `Marocco`, `Spagna`, `Olanda` gibi metinlerde şu kelime türleri sonucu etkileyebilir:

- yer adları
- etnonimler
- dini/kültürel adlandırmalar
- kurum ve mekân adları
- yolculuk nesneleri
- sık tekrar eden şehir/topografya söz varlığı

Bu nedenle De Amicis demonstrator'da en az iki koşum tasarlanmalıdır:

1. **Original run**
   - Metinler temel Guided ayarlarla çalışır.

2. **Toponym-clean run**
   - Yer adları ve belirgin coğrafi adlandırmalar çıkarılır ya da işaretlenir.
   - Sonuç korunuyorsa stil iddiası güçlenir.
   - Sonuç çöküyorsa bulgu büyük ölçüde topic/geography kaynaklı olabilir.

v0.1'de tam NER sistemi şart değildir. Başlangıç için:

- kullanıcı tarafından sağlanan stoplist
- demo corpus'a özel toponym listesi
- `custom_exclusions.txt`

yeterlidir.

Site uyarı metni:

> Geography view may be driven by place names and ethnonyms. Run the toponym-clean check before making a claim about style.

Yasak yorum:

- "Coğrafya üslubu kanıtlanabilir biçimde değiştirmiştir."
- "Costantinopoli'nin farklılığı doğrudan İstanbul deneyiminden kaynaklanır."
- "Yer adları çıkarılmadan bu bulgu stil farkıdır."

Doğru yorum:

> The result remains similar after removing place names, which strengthens the interpretation that the pattern is not only driven by geography-specific vocabulary.

### 4. Sonuç Kartlarında Ne Gösterir / Ne Göstermez

Her sonuç ekranında grafiklerden önce şu iki kutu bulunmalıdır:

**What this shows**

- seçili corpus içinde stilometrik yakınlık
- belirli ayarlar altında distance profile
- MFW değerleri arasında kararlılık veya kırılganlık
- corpus health'e bağlı yorum riski

**What this does not show**

- kesin yazarlık kanıtı
- edebi kalite
- nedensellik
- biyografik veya psikolojik durum
- coğrafyanın üslubu kesin biçimde değiştirdiği
- corpus dışında kalan yazar/metin ihtimalleri

Unknown text akışında ayrıca open-set uyarısı göster:

> The true author or closest comparison may be outside your corpus. Delta only compares against the texts you uploaded.

### 5. Demo Onboarding Görevleri

Demo corpus yalnızca "örnek çalıştır" düğmesi olmamalıdır. Kullanıcıya küçük araştırma görevleri vermelidir.

Quick Demo görevleri:

- MFW 100'den 500'e çıkınca en yakın komşu değişiyor mu?
- Dendrogram ile distance matrix aynı hikâyeyi mi anlatıyor?
- Sonuç stable mı, partially stable mı, unstable mı?

De Amicis demo görevleri:

- `Costantinopoli`, `Marocco`ya mı, `Spagna`ya mı daha yakın?
- Yer adları çıkarılınca bu yakınlık korunuyor mu?
- Corpus health uyarıları yorumu nasıl sınırlıyor?

Method Demo görevi:

- LDA topic sonucu ile Delta style sonucu aynı şeyi mi gösteriyor?
- LDA "ne hakkında?", Delta "nasıl yazılmış?" sorusunu nasıl ayırıyor?

### 6. Teknik Kuyruk ve Sunucu Koruma Kararları

Delta mevcut Lemmata sunucusunda çalışacaksa `lda.lemmata.app` etkilenmemelidir.

v0.1 teknik kararları:

- ayrı Unix user
- ayrı systemd service
- ayrı Python environment
- ayrı R/renv environment
- ayrı port: `127.0.0.1:8502`
- ayrı job klasörü: `/var/lib/lemmata-delta/jobs/<uuid>/`
- Caddy body limit
- systemd memory/CPU/runtime limitleri

Concurrency kararı:

- aynı anda en fazla 1 aktif R job
- en fazla 3 bekleyen job
- kuyruk doluysa kullanıcıya açık mesaj

Kuyruk mesajı:

> Delta is processing another corpus. Your job is queued. You can keep this page open or download the demo results while waiting.

Upload limitleri:

- `.zip` max 25-50 MB
- tek `.txt` veya `.csv` max 10 MB
- nested ZIP yasak
- absolute path ve `../` yasak
- symlink/hardlink yasak
- binary dosya reddedilir
- bozuk encoding kullanıcıya açıklanır

Encoding kararı:

- UTF-8 tercih edilir.
- Windows-1252 / ISO-8859-1 tespit edilirse kullanıcıya "converted to UTF-8" bilgisi verilir.
- Tespit edilemeyen encoding job'ı bloklar.
- Unicode normalization: NFC.

Job cleanup:

- tamamlanan joblar en geç 24 saat içinde silinir
- başarısız veya yarım joblar en geç 6 saat içinde silinir
- ham metinler application log'a yazılmaz
- hashler server'da kalıcı tutulmaz

### 7. FAIR-lite Paket Sertleştirmesi

FAIR-lite export paketi şu dosyaları da içermelidir:

```text
methods.md
limitations.md
rerun_instructions.md
RIGHTS.md
DATA-SOURCES.csv
CITATION.cff
processing_log.json
corpus_health.json
checksums.sha256
data_availability.md
```

Güncellenmiş v0.1 paket:

```text
delta-lemmata-fair-export-YYYYMMDD-HHMM.zip
  README.md
  methods.md
  limitations.md
  rerun_instructions.md
  RIGHTS.md
  CITATION.cff
  metadata.json
  manifest-sha256.json
  checksums.sha256
  parameters.json
  processing_log.json
  corpus_health.json
  environment.json
  data_availability.md
  data/
    DATA-SOURCES.csv
    document_inventory.csv
    feature_matrix.csv
  results/
    delta_distances.csv
    nearest_neighbors.csv
    summary.json
    mfw_robustness.csv
  figures/
    main_visualization.png
```

`DATA-SOURCES.csv` zorunlu alanları:

- text_id
- title
- author
- author_death_year
- first_publication_year
- edition_used
- source_url
- source_license
- accessed_at
- public_domain_basis
- sha256_original
- sha256_cleaned
- cleaning_notes
- public_demo_ok

`RIGHTS.md` açıklamalı:

- raw text pakete dahil mi?
- results hangi lisansla paylaşılabilir?
- metadata hangi lisansla paylaşılabilir?
- üçüncü taraf metinlerin hak durumu nedir?
- export paketi kaynak metin telifini değiştirmez

Varsayılan export hâlâ:

> FAIR Package, no raw texts.

### 8. Demo Corpus Hak Kontrolü

Public demo corpus ancak hak kontrolü tamamlandıktan sonra eklenebilir.

Kontrol checklist:

- yazar ölüm tarihi doğrulandı mı?
- ilk yayın yılı doğrulandı mı?
- kullanılan dijital kaynak kaydedildi mi?
- kaynak lisansı kaydedildi mi?
- modern önsöz, not, aparat, kapak, biyografi ve site metni çıkarıldı mı?
- çeviri, editör, illüstratör, kritik edisyon riski kontrol edildi mi?
- original SHA-256 ve cleaned SHA-256 alındı mı?
- cleaning log yazıldı mı?
- `public_demo_ok` kararı ve gerekçesi kaydedildi mi?

LiberLiber için karar:

- yalnız eser gövdesi alınır
- sinopsis, biyografi, kapak, site metni alınmaz
- kaynak lisansı `DATA-SOURCES.csv` içine yazılır

Project Gutenberg / Internet Archive için karar:

- tek başına hak güvencesi sayılmaz
- ülke, lisans ve kaynak kontrolü yapılmadan public demo'ya alınmaz

### 9. Privacy ve Etik Metinleri

Upload öncesi göster:

> Uploaded texts are processed temporarily to run the analysis. Delta does not require login, does not use external AI APIs, and does not store uploaded text after the job is completed. Upload only texts you have the right to process.

Checkbox:

> I confirm that I have the right or lawful basis to process these texts, and that I will not upload sensitive personal data or confidential material.

Privacy kararları:

- no login
- no external AI/API
- no analytics by default
- uploaded files temporary job folder'da tutulur
- raw text logs'a yazılmaz
- server security logs IP, timestamp, user agent, error status içerebilir
- security logs en fazla 7 gün tutulur
- export ZIP kullanıcı için üretilir, Delta kalıcı kopya saklamaz
- hashler server-side tracking identifier olarak tutulmaz

### 10. Makale Stratejisi Sertleştirmesi

Makale Delta tool description olarak yazılmamalıdır. Makalede başrol De Amicis problemi olmalıdır; Delta ölçüm ve belirsizlik aracı olarak kullanılmalıdır.

Güçlü makale hattı:

> Style Over Geography: An Uncertainty-Aware Delta Workbench for Reading De Amicis's Costantinopoli

Makale tezi:

> Delta, Burrows Delta'yı yazarlık atfı için değil, edebi yorumda belirsizliği görünür kılan yakın-uzak okuma arayüzü olarak yeniden konumlandırır. De Amicis vakası, coğrafi temsil, anlatı modu ve üslup arasındaki ilişkinin ancak parametre duyarlılığı ve topic-style kontrolleriyle yorumlanabileceğini gösterir.

Araştırma soruları:

1. `Costantinopoli` segmentleri coğrafi rota, bölüm sırası veya anlatı modu değişkenlerinden hangisine daha güçlü biçimde yakınsar?
2. Yer adları ve etnik/dini adlandırmalar çıkarıldığında Style Over Geography bulgusu korunur mu?
3. Delta sonuçları MFW, chunk uzunluğu ve preprocessing değiştiğinde ne kadar kararlı kalır?
4. Stilometrik kümeler yakın okumayla açıklanabilir mi?
5. Bir DH aracı belirsizliği saklamak yerine görünür kıldığında edebi yorumun güvenilirliği nasıl değişir?

Makale için siteye eklenirse çok değerli olacak özellikler:

- Reproduce this case study butonu
- her grafikte parametre rozeti
- Remove toponyms seçeneği
- toponym-clean karşılaştırma tablosu
- data availability notu
- FAIR-lite export bundle
- canlı URL + archived fallback

### 11. Güncellenmiş Geliştirme Öncelikleri

P010: Validation hardening
- stylo parity fixture
- known-author sanity fixture
- negative control fixture
- MFW robustness acceptance logic

P011: De Amicis demonstrator hardening
- `custom_exclusions.txt`
- toponym-clean run
- DATA-SOURCES.csv for demo texts
- RIGHTS.md for demo corpus

P012: Queue and resource protection
- one active R job
- max three queued jobs
- timeout and process cleanup
- job status messages

P013: FAIR-lite package hardening
- RIGHTS.md
- CITATION.cff
- DATA-SOURCES.csv
- processing_log.json
- corpus_health.json
- data_availability.md

P014: UX guardrails
- What this shows / What this does not show cards
- open-set warning
- demo tasks
- accessible stable/partial/unstable labels

P015: Publication readiness
- Reproduce this case study button
- parameter badges on figures
- archived/static fallback plan
- Umanistica Digitale article notes

## Kabul Kriterleri

MVP tamamlandı sayılması için aşağıdaki kapıların tamamı kanıtlanmalıdır. "Ekranda çalışıyor" tek başına yeterli değildir.

### P0 Kapsam ve Güvenlik Kapıları

- P000 teknik sözleşme kullanıcı tarafından onaylanmış olmalıdır.
- AI, dış API, analytics, login, kullanıcı hesabı ve kalıcı proje saklama eklenmemiş olmalıdır.
- Yalnız `.txt`, `.zip`, metadata `.csv` kabul edilmelidir.
- PDF, DOCX, EPUB, TEI ve OCR dosyaları açıklayıcı hata mesajıyla reddedilmelidir.
- ZIP upload güvenliği şu testleri geçmelidir: path traversal, absolute path, nested zip, symlink, hardlink, decompression bomb, dosya sayısı limiti, boyut limiti, MIME mismatch, binary file, null byte, duplicate filename, Unicode NFC/NFD çakışması, çok uzun dosya adı, boş metin, tek devasa token, CSV formula injection, metadata newline/path injection, bozuk encoding.
- `Rscript` her zaman `shell=False` ile, belirli `cwd`, temiz environment ve timeout ile çalışmalıdır.
- Aynı anda en fazla 1 aktif R job ve en fazla 3 bekleyen job olmalıdır.
- Başarılı joblar en geç 24 saat, başarısız veya yarım joblar en geç 6 saat içinde silinmelidir.
- Application log, R stdout/stderr, Caddy log ve systemd journal ham metin içermemelidir.
- Security loglarda ham text, metadata içeriği veya dosya içeriği bulunmamalıdır; retention en fazla 7 gün olmalıdır.

### P0 Metodoloji Kapıları

- Kanonik metodoloji şudur: Classic Burrows Delta, surface word forms, lowercase on, punctuation/numbers removed, stopword removal off, lemmatization off, MFW 100/300/500/1000.
- 1000 MFW mümkün değilse analiz başarısız sayılmaz; sistem `not enough features` uyarısı üretir ve bunu export'a yazar.
- `micro_delta_gold` fixture corpus doğrudan R `stylo` ve Delta üzerinden çalıştırıldığında feature list aynı olmalı, distance matrix toleransı `1e-6` içinde kalmalı, nearest-neighbor sırası aynı olmalıdır.
- Known-author sanity fixture makul nearest-neighbor örüntüsü üretmelidir.
- Negative control fixture sistemin her karşılaştırmadan güçlü sonuç çıkarmadığını göstermelidir.
- Unknown text varsa open-set uyarısı gösterilmeli ve `unknown_in_feature_calibration` alanı raporda yer almalıdır.
- MFW robustness etiketi yalnız "aynı gruba düştü" diye verilmemelidir; nearest group, nearest neighbor, rank, margin ve cluster placement birlikte değerlendirilmelidir.
- PCA varsa explained variance, MDS varsa stress değeri gösterilmelidir.
- Stopword removal açılırsa uyarı verilmeli; lemmatization açılırsa sonuç `experimental` etiketi almalıdır.
- Toponym-clean run maskeleme ile değil, `custom_exclusions.txt` üzerinden feature dışlama ile yapılmalıdır.

### P0 Ürün ve UX Kapıları

- Kullanıcı `.zip` içinde `.txt` dosyaları yükleyebilmelidir.
- Metadata tablosu düzenlenebilmeli veya CSV import edilebilmelidir.
- Corpus health check bloklayıcı, uyarı ve bilgi düzeyleriyle çalışmalıdır.
- Guided Mode tek akışla 100/300/500/1000 MFW analizlerini çalıştırmalıdır.
- Dendrogram, PCA veya MDS, distance matrix ve nearest-neighbor tablosu gösterilmelidir.
- Her görselde parameter badge bulunmalıdır: MFW, distance, cluster method, culling, preprocessing, projection quality.
- Sonuç ekranında "What this shows" ve "What this does not show" kartları bulunmalıdır.
- Arayüz kesin yazarlık, nedensellik, edebi kalite veya psikolojik durum iddiası kurmamalıdır.
- Her sonuçta şu anlam korunmalıdır: Bu sonuç yalnızca yüklenen corpus içindeki stilometrik yakınlığı gösterir; corpus dışındaki yazar veya metin ihtimallerini dışlamaz.

### P0 FAIR ve Reproducibility Kapıları

- Varsayılan export `FAIR Package, no raw texts` olmalıdır.
- Export ZIP içinde kanonik dosyaların tamamı bulunmalıdır: `README.md`, `methods.md`, `limitations.md`, `rerun_instructions.md`, `RIGHTS.md`, `CITATION.cff`, `metadata.json`, `manifest-sha256.json`, `checksums.sha256`, `parameters.json`, `processing_log.json`, `corpus_health.json`, `environment.json`, `data_availability.md`, `data/DATA-SOURCES.csv`, `data/document_inventory.csv`, `data/feature_matrix.csv`, `results/delta_distances.csv`, `results/nearest_neighbors.csv`, `results/summary.json`, `results/mfw_robustness.csv`, `figures/main_visualization.png`.
- `environment.json` Python, R, `stylo`, package versions, locale, Unicode normalization, git commit ve stylo args bilgilerini içermelidir.
- Aynı corpus + aynı `parameters.json` + aynı environment ile normalize edilmiş export karşılaştırmasında `feature_matrix.csv`, `delta_distances.csv`, `nearest_neighbors.csv` ve `mfw_robustness.csv` aynı olmalıdır.
- `checksums.sha256` doğrulanmalıdır.
- Default export ham metin içermemelidir.
- Full Research Object ham metin eklemeyi ancak açık opt-in ve hak kontrolüyle yapmalıdır; v0.1 public default değildir.
- Demo corpus `public_demo_ok=true` ve `RIGHTS.md` tamamlanmadan public siteye eklenmemelidir.
- `feature_matrix.csv` derived data olarak etiketlenmelidir.

### P0 Deployment Kapıları

- Delta ayrı Unix user, ayrı Python venv, ayrı R/renv, ayrı systemd service, ayrı job klasörü ve ayrı portla çalışmalıdır.
- Port varsayımı: `delta.lemmata.app -> 127.0.0.1:8502`; `lda.lemmata.app -> 127.0.0.1:8501`.
- Caddy yalnız localhost portuna reverse proxy yapmalıdır.
- systemd unit resource limitleri içermelidir: memory, CPU, runtime timeout, restart policy, working directory, environment file, state/log/runtime directory.
- `lda.lemmata.app` canlı smoke testten geçmeden Delta tamamlanmış sayılmaz.

## Codex Son Denetim Checklist

Bu proje Claude Code ile geliştirildikten sonra Codex soru sormaz, kanıt ister. Claude'un "bitti" demesi yeterli değildir.

Codex final audit şunları çalıştırmalı veya kanıtını istemelidir:

1. Clean clone kurulumu: README adımlarıyla sıfırdan kurulum.
2. Unit testler: parser, metadata schema, preprocessing, export builder, queue state machine.
3. Integration testler: Streamlit/Python katmanı, R `stylo` wrapper, job lifecycle.
4. Security testler: `bad_upload_pack` içindeki adversarial upload örnekleri.
5. `micro_delta_gold` stylo parity: feature list eşleşmesi, distance matrix `1e-6`, nearest-neighbor sırası.
6. `same_corpus_three_formats`: aynı corpus `.txt`, `.zip`, `.csv metadata` ile aynı iç modele ve aynı sonuca dönmeli.
7. `encoding_and_labels`: UTF-8, Windows-1252, aksanlı dosya adları, uzun dosya adları.
8. `performance_medium`: 15-25 metin ve 5k-20k kelime aralığında timeout ve memory limit testi.
9. `de_amicis_topic_style`: original run ve toponym-clean run üretimi.
10. MFW 100/300/500/1000 koşularının gerçekten tamamlandığı veya 1000 için `not enough features` uyarısı verdiği.
11. FAIR export normalize edilmiş tekrar üretim testi.
12. Export ZIP içinde zorunlu dosyaların tamamının varlığı ve checksum doğrulaması.
13. Default export içinde raw text bulunmadığı.
14. Log taraması: application log, R stderr/stdout, Caddy log, systemd journal içinde ham metin yok.
15. UI metin taraması: "proves", "definitely", "written by" gibi kesin yazarlık ifadeleri yok.
16. No AI/API/analytics taraması: OpenAI, Anthropic, Google Analytics, tracking script veya dış inference endpoint yok.
17. Public demo corpus hak dosyaları: `DATA-SOURCES.csv`, `RIGHTS.md`, `public_demo_ok`.
18. Canlı smoke test: `https://delta.lemmata.app` 200 döner, analiz çalışır, export iner.
19. Komşu servis smoke test: `https://lda.lemmata.app` etkilenmemiştir.
20. Deployment izolasyonu: ayrı user, ayrı env, ayrı service, ayrı port, ayrı job directory.

## İlk Geliştirme Planı

P000: Technical implementation contract
- kod yazmadan önce kapsam kilidi
- çelişki çözümü
- metodoloji protokolü
- upload güvenliği planı
- job queue planı
- LDA izolasyon planı
- P001-P015 sırası
- en fazla 7 bloklayıcı soru

P001: Repo scaffold, config ve test altyapısı
- Streamlit shell
- proje klasörleri
- config dosyaları
- test runner
- minimal README

P002: Local app shell ve health check
- `127.0.0.1` bind
- port/env ayarları
- health endpoint veya health sayfası
- basic navigation

P003: Upload security ve extraction sandbox
- `.txt`, `.zip`, `.csv` kabulü
- ZIP validation
- charset detection
- NFC normalization
- adversarial upload testleri

P004: Metadata schema ve corpus inventory
- required fields
- CSV import/export
- metadata editor
- document inventory
- known/unknown handling

P005: Job lifecycle ve queue
- `uploaded -> validated -> queued -> running -> succeeded/failed/expired`
- 1 active R job
- 3 queued jobs
- timeout
- cleanup policy

P006: R `stylo` wrapper
- `run_stylo.R`
- `shell=False` subprocess
- fixture corpus
- direct stylo parity baseline
- timeout and stderr sanitization

P007: Preprocessing ve corpus health
- lowercase
- punctuation/number removal
- surface forms
- stopword removal off
- lemmatization off
- word counts and group checks

P008: Guided analysis orchestration
- MFW 100/300/500/1000
- Classic Burrows Delta
- unknown holdout rule
- failed MFW handling
- reproducible parameters

P009: Results UI
- summary cards
- dendrogram
- PCA or MDS
- distance matrix
- nearest neighbors
- parameter badges

P010: Validation hardening
- `micro_delta_gold`
- known-author sanity
- negative control
- stylo parity report
- tolerance and failure criteria

P011: MFW robustness panel and guardrails
- stable/partial/unstable logic
- nearest group, neighbor, rank, margin, cluster placement
- What this shows / What this does not show
- open-set warning

P012: FAIR-lite export
- kanonik ZIP dosya listesi
- no raw texts default
- checksum verification
- environment capture
- rerun instructions

P013: De Amicis demonstrator
- hak kontrolü bitmeden public corpus yok
- `Spagna`, `Olanda`, `Marocco`, `Costantinopoli`
- original run
- toponym/ethnonym-clean run
- `custom_exclusions.txt`

P014: Deployment hardening
- separate Unix user
- separate Python venv
- separate R/renv
- separate systemd service
- Caddy route
- cleanup timer
- live smoke test

P015: Documentation and publication readiness
- user guide
- methodology note
- privacy note
- validation plan
- Umanistica Digitale article notes
- Codex final audit handoff

## Claude Code'a Verilecek İlk Prompt

```text
P000: Delta technical implementation contract

CLAUDE.md dosyasını tamamen oku. Kod yazma. Önce teknik sözleşme çıkar:
1. v0.1 kapsam kilidi
2. çelişen kararların çözümü
3. kanonik metodoloji protokolü
4. job queue ve resource limit planı
5. upload güvenliği planı
6. aynı Hetzner sunucuda lda.lemmata.app izolasyon planı
7. P001-P015 uygulanabilir sıra
8. en fazla 7 bloklayıcı soru

Onay almadan scaffold başlatma. AI/API ekleme. LDA uygulamasına dokunma. Public demo corpus'u hak kontrolü bitmeden ekleme.
```

## Kapanış Notu

Delta'nın değeri "stilometriyi kolaylaştırmak" ile sınırlı kalmamalıdır. Esas değer, stilometriyi yanlış kesinlikten koruyarak öğretmek, ayarların etkisini görünür kılmak ve her sonucu tekrar üretilebilir bir araştırma paketine dönüştürmektir.

Bu çizgi korunursa Delta, Lemmata ailesinin doğal ikinci aracı olur:

```text
lda.lemmata.app     -> metinler ne hakkında?
delta.lemmata.app   -> metinler nasıl yazılmış?
```
