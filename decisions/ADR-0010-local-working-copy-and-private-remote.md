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

## Generated Environment Cleanup Follow-up

Kullanıcı, Drive'ın eski yükleme kuyruğunda yalnız yeniden üretilebilir Python ve
araç dosyaları kaldığı doğrulandıktan sonra provider Trash içindeki `.venv` ve
`.tools` dizinlerinin kalıcı silinmesini açıkça onayladı.

- Silme öncesinde iki hedefin beklenen repository kökü altında gerçek dizin olduğu,
  symlink olmadığı ve eski kopyanın `.git/HEAD` işaretini taşıdığı doğrulandı.
- Yeni yerel repository, yeni `.venv`, yeni `.tools`, etkin branch ve uygulama
  health endpoint'i ayrı koruma kapıları olarak kontrol edildi.
- Eski generated dizinlerin toplamı yaklaşık 646 MiB idi. Yalnız bu iki dizin
  silindi; eski kaynak kodu ve `.git` provider Trash içinde korundu. Kalan eski
  kaynak kopyası yaklaşık 49 MiB'dir.
- Drive'ın ilk normal kapanış isteği aktif senkronizasyon onayında bekledi. Açık
  onay penceresi `Tamam` ile kapatıldı ve uygulama temiz biçimde yeniden başlatıldı.
- Drive'ın operasyon veritabanı yalnız salt okunur incelendi. Bekleyen kayıtların
  okunabilen adları generated `.pyi` ve dependency dosyalarıydı; Drive'ın iç
  veritabanı veya cache dosyaları elle değiştirilmedi.
- Operasyon sayısı dalgalar hâlinde boşaldıktan sonra 60 saniye kesintisiz sıfır
  kaldı. Drive arayüzü `Güncel` durumunu gösterdi.
- Bu temizlik P003 kodunu, acceptance durumunu veya exact implementation kanıtını
  değiştirmez.

## Provider Trash Final Closure Correction

Yukarıdaki 60 saniyelik sıfır kuyruk ve `Güncel` gözlemi o anda doğruydu, fakat
nihai kapanış için yetersiz kaldı. Sonraki gözlemde provider Trash içindeki eski
çalışma ağacı yeni işlem dalgaları üretmeye devam etti. Bu bölüm önceki kaydı
silmez; geçici kapanışı ve onu izleyen düzeltmeyi ardışık olarak belgeler.

- `.venv` ve `.tools` sonrasında kalan `.coverage`, `.mypy_cache`,
  `.pytest_cache`, `.ruff_cache`, `build`, `renv/library`, `__pycache__` ve
  `src/delta_lemmata.egg-info` yolları `git check-ignore` ile yeniden üretilebilir
  oldukları doğrulandıktan sonra eski Trash kopyasından kaldırıldı. P001 generated
  evidence bu aşamada korundu.
- İlk sıfır kuyruğun ardından eski `.git` nesneleri ve P001 kanıt dosyaları yeni
  local-only create dalgaları olarak belirdi. Kök neden, yaklaşık 13 MiB'lık eski
  repository'nin 792 dosya ve 292 dizinle hâlâ Drive'ın yönettiği provider Trash
  alanında bulunmasıydı.
- Normal kapanış `StopAllAccounts with SUCCESSFUL_EXIT` sonrasında tamamlanmadı.
  Bekleyen operasyon sayısı sıfır ve `lost_and_found` boşken, yalnız takılı
  `Google Drive --single_process` yardımcı süreci önce `TERM`, yanıt vermeyince
  `KILL` ile kapatıldı. Yeniden başlatma 10.654 change-log girdisini yerel çalışma
  kümesiyle uzlaştırdı; bu olay yeni Delta yüklemesi değil Drive metadata
  reconciliation işlemiydi.
- Provider alanından doğrudan `mv` ve ardından kontrollü `rsync` denemeleri File
  Provider timeout'u verdi. Doğrudan taşıma hedef oluşturulmadan sonlandı; kısmi
  `rsync` hedefi kaldırıldı. Bu başarısız denemeler eski kaynak kopyasını veya
  kanonik repository'yi değiştirmedi.
- Eski Trash kopyası kaldırılmadan önce
  `~/Developer/_migration_archive/delta-lemmata-safety-20260711` altında 5,1 MiB
  güvenlik paketi oluşturuldu. Paket, tam geçmişli 11 ref içeren ve
  `git bundle verify` kapısını geçen `delta.lemmata_app-all-refs.bundle` dosyasını,
  onun `03b0e84f69db188a927ca5c7194aaad2054f869b98845d3d7b3b07a74f970737`
  SHA-256 değerini ve Git dışındaki sekiz P001 generated evidence dosyasının ayrı
  SHA-256 manifestini içerir.
- Kanonik `HEAD` ve özel GitHub dalı
  `3adfca0221980ccc827d3384317bb42d4dee15f0` değerinde eşleşti; uygulama health
  endpoint'i `ok` döndürdü. Bu kapılardan sonra yalnız provider Trash içindeki eski
  ve artık yedek olan `delta.lemmata_app` kopyası kalıcı olarak kaldırıldı.
- Nihai gözlemde Drive arayüzü en az altı dakika boyunca `Güncel` kaldı;
  `operations=0` ve local-only item sayısı `0` olarak doğrulandı. Görünen son üç
  öğe Delta'ya ait değildi ve yeşil onaylı tamamlanmış indirmelerdi.
- Drive'ın iç SQLite kayıtları yalnız salt okunur sorgulandı. Global cache
  temizlenmedi, hesap bağlantısı kesilmedi ve başka Drive verisi değiştirilmedi.
  Bu operasyon P003 kodunu veya insan kabul durumunu değiştirmez.
