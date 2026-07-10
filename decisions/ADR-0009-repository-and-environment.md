# ADR-0009: Repository and Environment Baseline

**Durum:** Kabul edildi  
**Tarih:** 2026-07-10  
**Ticket:** P001

## Bağlam

Delta klasörü kullanıcı kararıyla `AKADEMİK-ASİSTAN` altında tutulmaktadır. Üst klasör, kişisel ve akademik içeriği barındıran ayrı bir yerel Git deposudur. Delta'nın FAIR-oriented biçimde public yayımlanması planlandığı için iki geçmişin birbirine karışması hassas veri, telif ve provenance riski oluşturur.

Yerel denetimde şu ortam bulundu:

- macOS 26.5.1, Apple Silicon arm64
- Python 3.13.9, Anaconda dağıtımı
- R 4.5.2
- Git 2.53.0
- `uv`, `renv`, `stylo` ve Docker başlangıçta kurulu değil

## Karar

### Repository Sınırı

- `delta.lemmata_app/`, kendi `.git` dizini olan bağımsız repository olacaktır.
- Üst `AKADEMİK-ASİSTAN` deposu bu klasörü `.gitignore` ile tamamen dışarıda tutar.
- Delta bir Git submodule değildir. Üst depoya gitlink veya Delta dosyaları eklenmez.
- Public remote, kullanıcı GitHub repository'sini oluşturduktan ve P001 secret/path scan geçtikten sonra eklenir.
- Planlanan repository adı `delta-lemmata`dır; remote oluşturulmadan URL kanonik metadata'ya yazılmaz.
- Default branch `main`, ticket branch'leri gerektiğinde `codex/` veya araçtan bağımsız `p0xx-*` adlandırmasıyla açılır.

### Lisans ve Atıf

- Yazılım kodu MIT License ile yayımlanır; bu Lemmata'nın mevcut lisansıyla uyumludur.
- İlk yazılım copyright sahibi Oğuz Koran'dır.
- Software citation metadata başlangıçta yalnız gerçekleşmiş katkıları gösterir. Barış Yücesan P015 validation katkısı tamamlandığında contributor/author metadata'sı CRediT ile yeniden değerlendirilir.
- Corpus, edisyon ve diğer veri varlıkları MIT kapsamına otomatik olarak girmez; her biri asset-level rights kaydı taşır.

### Canonical Runtime

- Python baseline: CPython 3.13; exact local patch 3.13.9. `requires-python` aralığı `>=3.13,<3.14` olur.
- R baseline: R 4.5; exact local patch 4.5.2.
- Python dependencies `uv.lock`, R dependencies `renv.lock` ile kilitlenir.
- Yerel macOS geliştirme ortamıdır. Bilimsel ve production kanıt ortamı Linux x86_64 OCI image olacaktır.
- Container base image tag ve digest birlikte pinlenir. Docker yerelde bulunmadığı için image build/run acceptance sonucu kanıtlanana dek `not verified` kalır.
- Native Anaconda environment canonical sonuç üretmez; yalnız bootstrap için kullanılır. Proje komutları repository-local `.venv` veya canonical container içinde çalışır.

### Sürüm ve Metadata

- Tek kanonik sürüm kaynağı kökteki `VERSION` dosyasıdır.
- Başlangıç sürümü `0.0.0.dev0`dır; bu bir public v0.1 release değildir.
- Package metadata, CFF ve CodeMeta tutarlılığı otomatik testle denetlenir.
- Henüz var olmayan DOI, SWHID, remote URL veya release tarihi metadata'ya uydurulmaz.

## Alternatifler

### Üst Akademik Asistan Deposunda Tutmak

Reddedildi. Private vault ile public yazılım geçmişini karıştırır ve yanlışlıkla hassas içerik yayımlama riskini yükseltir.

### Git Submodule Kullanmak

Reddedildi. Üst depo için uzak remote yoktur ve submodule kullanıcıya gereksiz operasyon yükü getirir. Ignore edilmiş bağımsız nested repository daha basittir.

### Delta'yı Akademik Asistan Klasörü Dışına Taşımak

Şimdilik reddedildi. Kullanıcının seçtiği çalışma düzenini bozar. Bağımsız repository sınırı aynı gizlilik amacını taşımadan sağlar.

## Sonuçlar

- Delta public Git geçmişi akademik asistan kasasından ayrılır.
- Claude ve Codex çalışma kökü olarak doğrudan `delta.lemmata_app` klasörünü açar.
- Parent repo, Delta dosyalarını staged veya committed göstermez.
- GitHub remote ve ilk public push ayrı, kullanıcı tarafından görünür bir işlem olur.
- Docker bulunmadığı için container verification P001 içinde açık kanıt eksiği olarak raporlanabilir; gizlenmez.
