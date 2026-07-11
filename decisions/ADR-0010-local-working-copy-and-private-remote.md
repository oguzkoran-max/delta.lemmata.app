# ADR-0010: Local Working Copy and Private GitHub Remote

**Durum:** Kabul edildi  
**Tarih:** 2026-07-11  
**Kapsam:** Repository operations; P003 acceptance durumunu değiştirmez

## Bağlam

ADR-0009, Delta'yı bağımsız bir Git repository olarak kurmuş fakat kullanıcının o
günkü tercihiyle çalışma klasörünü Google Drive altındaki `AKADEMİK-ASİSTAN`
dizininde bırakmıştı. Repository-local `.venv`, R library ve araç önbellekleri
binlerce küçük dosya üretti. Google Drive bunları sürekli eşitlemeye çalıştığı için
hem Drive kullanımı hem de geliştirme akışı bozuldu.

P003 dalı temizdi ve bütün Git geçmişi yerelde bulunuyordu, fakat uzak yedek henüz
yoktu. Taşıma sırasında kod, Git geçmişi, göz ardı edilen kanıt çıktıları ve aktif
ticket durumu kaybedilmemeliydi.

## Karar

- Kanonik yerel çalışma kopyası `~/Developer/delta.lemmata_app` olacaktır.
- `origin`, Oğuz Koran'ın `oguzkoran-max` hesabındaki özel
  `https://github.com/oguzkoran-max/delta.lemmata.app` repository'sidir.
- Varsayılan uzak dal `main`dir. Mevcut bütün dallar ve etiketler uzak depoya
  gönderilir; aktif geliştirme `codex/p003-secure-ingestion` dalında sürer.
- Google Drive artık Delta kodu, Git geçmişi veya geliştirme ortamı için kaynak
  değildir. Eski klasör, doğrulanmış temiz klondan sonra geri alınabilir biçimde
  macOS Çöp Kutusu'na taşınır.
- `.venv`, `.tools`, cache ve build çıktıları Git'e veya Drive'a alınmaz. Ortam,
  `./scripts/bootstrap.sh` ile kilit dosyalarından yeniden üretilir.
- Git tarafından göz ardı edilen P001 generated evidence, taşıma sırasında ayrı
  olarak korunur. Gelecek release kanıtı yalnız repository'de izlenen veya
  deterministik olarak yeniden üretilen artefaktlara dayanır.
- Drive içinden yeni yerel klasöre sembolik bağlantı oluşturulmaz. Claude Code,
  Codex ve VS Code doğrudan kanonik yerel yolu açar.
- Özel GitHub repository'si bir public release değildir. Public görünürlük,
  metadata URL'leri, archival deposit ve DOI ayrı release kapısında ele alınır.

## Taşıma Kapıları

1. Eski çalışma ağacı temiz ve exact commit kaydedilmiş olmalı.
2. Özel GitHub repository'sinin görünürlüğü ve varsayılan dalı doğrulanmalı.
3. Bütün dallar ve etiketler gönderilmeli.
4. GitHub'dan yeni yerel klon alınmalı ve aktif dala geçilmeli.
5. P001 generated evidence eski ve yeni kopyada birebir eşleşmeli.
6. Yeni klonda bootstrap ve tam verification geçmeli.
7. Ancak bu kapılardan sonra eski Drive klasörü Çöp Kutusu'na taşınmalı.

## Alternatifler

### Google Drive İçinde Devam Etmek

Reddedildi. Sanal ortam ve araç dosyalarının sürekli eşitlenmesi aynı darboğazı
yeniden üretir; yalnız klasör seçici ayarlarla çözüm kırılgan kalır.

### Masaüstüne Taşımak

Reddedildi. Teknik olarak çalışır, fakat kalıcı geliştirme repository'leri için
`~/Developer` daha düzenli ve araçlar arası daha açık bir kanonik köktür.

### Drive'da Sembolik Bağlantı Bırakmak

Reddedildi. Drive'ın symlink davranışı ek belirsizlik yaratır ve kaldırılmak istenen
Drive bağımlılığını görünüşte sürdürür.

### GitHub Olmadan Yalnız Yerel Kopya Tutmak

Reddedildi. Bilgisayar arızasına karşı uzak Git geçmişi olmaz ve Claude/Codex
geçişleri için ortak kanonik remote eksik kalır.

## Sonuçlar

- Günlük geliştirme Drive eşitlemesinden ayrılır.
- GitHub, izlenen kaynak ve geçmiş için uzak yedek olur; kullanıcı corpus'u veya
  göz ardı edilen runtime verileri otomatik olarak GitHub'a gönderilmez.
- Her yeni Claude, Codex veya VS Code oturumu
  `~/Developer/delta.lemmata_app` klasörünü açmalıdır.
- ADR-0009'daki “Delta'yı Akademik Asistan klasörü dışında tutmama” kararı ile
  remote henüz yok ifadeleri bu ADR tarafından kısmen geçersiz kılınır. Repository
  ayrımı, lisans, runtime ve metadata kararları geçerliliğini korur.
- P003, insan kabulü verilene kadar `in-progress` kalır.

## Uygulama Sonucu

- `oguzkoran-max/delta.lemmata.app` özel repository olarak oluşturuldu;
  görünürlük `PRIVATE`, varsayılan dal `main` olarak doğrulandı.
- `main`, `claude/p002-independent-audit`, `codex/p002-audit-corrections` ve
  `codex/p003-secure-ingestion` dalları uzak depoda doğrulandı.
- Yeni klon aktif P003 dalında `b8920cf` commit'ine getirildi. P001 generated
  evidence eski kopyayla birebir eşleşti.
- Kilit dosyalarından bootstrap geçti. Tam verification 232 test, yüzde 100
  statement/branch coverage, metadata, 27 provenance kaydı, repository scan ve
  R lock kapılarını geçti.
- İlk doğrudan `mv` denemesi bulut sağlayıcısı timeout'u verdi; Finder AppleScript
  denemesi provider nesnesini çözemedi. İki deneme de kaynak klasörü değiştirmeden
  sonlandı. Yerleşik `/usr/bin/trash` üçüncü denemede klasörü Google Drive biriminin
  Çöp Kutusu'na başarıyla taşıdı.
- Google Drive yeniden başlatıldı. Eski çalışma yolu yok, yeni yerel repository ve
  geri alınabilir Trash kopyası var.
