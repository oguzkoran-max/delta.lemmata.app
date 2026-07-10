# Delta Supported Environment Matrix

**Durum:** P001 sürüm baseline'ı kilitlendi; container build ve browser matrisi henüz doğrulanmadı  
**Tarih:** 2026-07-10

## 1. Destek İlkesi

Delta'nın bilimsel olarak kanonik çalışma ortamı, pinlenmiş Linux OCI image'dır. Mac'te native Python/R kurulumu geliştirme kolaylığı sağlayabilir, fakat makale parity veya reproducibility kanıtı sayılmaz. Bu ayrım, “benim bilgisayarımda çalışıyor” sonucunu destek iddiasına dönüştürmemek içindir.

## 2. Ortam Matrisi

| Ortam | Platform | Rol | Destek düzeyi | Zorunlu kanıt |
|---|---|---|---|---|
| Canonical runtime | Linux x86_64 OCI container | Python orchestration, Streamlit, R `stylo`, public service | Tam destek | P001 lock/install; P006 parity; P014 load/isolation |
| CI | GitHub-hosted Linux x86_64 veya eşdeğer temiz runner | Unit, integration, schema, security ve build kontrolleri | Tam destek | Her commit CI; release'te temiz build |
| Production | Mevcut VPS üzerindeki Linux x86_64 container runtime | `delta.lemmata.app` | Tam destek, P014 sonrası | Lemmata smoke, rollback, resource ve retention audit |
| Clean rerun | Temiz Linux x86_64 host ve pinlenmiş OCI image | FAIR package yeniden koşumu | Tam destek, P012 sonrası | İkinci ortam rerun ve checksum/tolerance raporu |
| Developer host | Apple Silicon macOS | Oğuz'un Codex/Claude geliştirme ortamı | Geliştirme desteği | Container build/test; native sonuç bilimsel kanıt değildir |
| Native macOS Python/R | Apple Silicon macOS | Hızlı yerel debug | Best effort | CI/canonical container sonucu ile doğrulama zorunlu |
| Windows native | Windows | Yerel geliştirme | v0.1'de desteklenmez | Yok; container/remote workflow kullanılabilir |
| Mobile browser | iOS Safari, Android Chrome | Upload durumu ve sonuç inceleme | Responsive smoke desteği | P002/P009 screenshot ve overflow testleri |
| Desktop browser | Güncel Chrome, Firefox, Safari | Ana workbench kullanımı | Tam UI desteği | P002/P008/P009 Playwright ve manual smoke |

## 3. Sürüm Politikası

- Python major/minor, R major/minor, `stylo`, Streamlit ve doğrudan dependencies P001'de lock edilir.
- Base image yalnız mutable tag ile kullanılmaz; digest kaydedilir.
- Exact patch sürümleri `VERSION` veya tek release manifestinden türetilir; README içine elle çoğaltılmaz.
- R session info, Python package inventory, locale, timezone, BLAS/LAPACK bilgisi ve container digest her bilimsel run paketine girer.
- Dependency update otomatik claim yükseltmez. P006 parity ve ilgili regression suite yeniden geçmeden canonical runtime değişmez.
- Cross-version stability ayrı bir çalışmadır; aynı image içindeki determinism ile karıştırılmaz.

### P001 Kilitli Baseline

| Bileşen | Kilitli değer | Kanıt |
|---|---|---|
| Python | CPython 3.13.9 | `.python-version`, `uv.lock` |
| Python resolver | uv 0.11.28 | `scripts/bootstrap.sh` |
| Streamlit | 1.59.1 | `uv.lock` |
| Pydantic | 2.13.4 | `uv.lock` |
| JSON Schema | jsonschema 4.26.0 | `uv.lock` |
| R | 4.5.2 | `renv.lock` |
| renv | 1.2.3 | `renv.lock` |
| stylo | 0.7.71 | `renv.lock` |
| jsonlite | 2.0.0 | `renv.lock` |
| Linux base | `rocker/r-ver:4.5.2` | `containers/base-images.lock.json` |
| Base manifest digest | `sha256:fd4ccdd3a4a6f7ef805e2daeee2a0fe3bf126bc231f36351223baecf5a595a4c` | Docker Registry API V2, 2026-07-10 |

Yerel Mac'te Docker ve XQuartz yoktur. Bu nedenle container build ile local
`stylo` namespace load doğrulanmış sayılmaz. Ayrıntı
`docs/development/local-runtime-limitations.md` içindedir.

## 4. Browser Politikası

- “Güncel” ifadesi release tarihinde support manifestine yazılan exact browser major sürümlerini ifade eder.
- Ana acceptance testleri desktop'ta 1440x900 ve 1280x800, mobile smoke testleri 390x844 ve 412x915 viewport'larında çalışır.
- Mobile'da tüm ileri ayarların rahatça düzenlenmesi zorunlu değildir; fakat metin taşması, kontrol çakışması, kayıp uyarı ve okunamaz sonuç kabul edilmez.
- Browser'da çalışan hesaplama yoktur; canonical sonuç server-side pinlenmiş runtime'dan gelir.

## 5. Destek Dışı Kombinasyonlar

- Kullanıcı tarafından değiştirilmiş R package setiyle üretilen sonuç canonical Delta sonucu sayılmaz.
- ARM container sonucu P006 parity ve P012 clean rerun geçmeden release kanıtı olarak kullanılmaz.
- Python/R native Windows kurulumu için v0.1 destek sözü verilmez.
- Eski browser'larda graceful error hedeflenir, fakat yöntemsel sonuç doğruluğu desteklenmiş sayılmaz.

## 6. P001 ve Release Kapısı

P001 şu değerleri doldurdu:

1. Python ve R exact sürümleri.
2. Package manager ve lock formatları.
3. Base image adı ve digest'i.
4. CI runner image'ı.
Browser test major sürümleri P002'de Playwright kurulurken doldurulacaktır.

P015 release manifesti, bu matristen hangi kombinasyonların gerçekten test edildiğini listeler. Test edilmemiş bir kombinasyon “supported” olarak ilan edilmez.
