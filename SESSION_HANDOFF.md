# Delta Session Handoff

**Güncellendi:** 2026-07-10  
**Aşama:** P001 tamamlandı; P002 başlamaya hazır
**Kod durumu:** Temel paket/provenance kodu var; kullanıcıya dönük ürün akışı yok
**Aktif ticket:** Yok
**Sıradaki tek ana iş:** P002 English-Only Workbench Shell

## Önce Oku

1. `START_HERE.md`
2. Bu dosya
3. Roadmap'teki yalnız P002 bölümü
4. `decisions/ADR-0001-product-and-paper.md`
5. `decisions/ADR-0008-scholarly-vibe-coding.md`
6. Claim CE-01, CE-18 ve CE-20
7. Threat SEC-14 ve EPI-13
8. `provenance/tickets/P001.json` ve P001 acceptance raporu

## P001 Sonucu

- Delta, akademik-asistan kökünden bağımsız `main` branch'li ayrı bir Git repository oldu.
- Repo topolojisi, ortam ve sürüm kararları ADR-0009'da kaydedildi.
- Python 3.13.9 ve R 4.5.2 ortamları `uv.lock` ve `renv.lock` ile kilitlendi.
- `stylo` 0.7.71 kilitli ana motor; Python/Streamlit orchestration katmanı olarak tanımlandı.
- VERSION, MIT LICENSE, CITATION.cff ve CodeMeta metadata tek `0.0.0.dev0` sürümünü gösteriyor.
- Altı versioned provenance/rights/release JSON Schema ve machine-readable örnek kayıtlar eklendi.
- PromptEvent, HumanDecision, Ticket ve Run ayrımı gerçek P001 kaydında uygulandı.
- CI action commit SHA'ları ve Linux amd64 container tabanı digest ile pinlendi.
- SBOM, dependency audit, secret/path/corpus scan ve metadata consistency komutları eklendi.
- `./scripts/bootstrap.sh` temiz Git klonunda iki ortamı yeniden kurdu.
- `./scripts/verify.sh` temiz klonda 24 testi, strict mypy ve bütün P001 kapılarını geçti.
- İlk implementation snapshot commit'i `26131a88a04d1d79ffe50d9eb9ee676d41c2072b`.
- Ürün UI'si, upload, gerçek `stylo` hesaplaması ve Pinokyo corpus'u P001'de uygulanmadı.

## Doğrulanmamış Sınırlar

- Docker bu Mac'te kurulu olmadığı için container henüz build edilmedi.
- GitHub remote olmadığı için CI sunucuda çalışmadı.
- macOS R/Tcl-Tk, `stylo` namespace yüklemesi için XQuartz istiyor.
- Gerçek `stylo` execution ve parity P006'nın Linux container acceptance işidir.
- CE-12, CE-18, CE-19 ve CE-20 yalnız `implemented`; son gate'leri geçmeden `verified` denmez.

Bu maddeler P001 sonucu içinde gizlenmiş pass değildir. İlgili sonraki ticket'lara
aktarılmış açık doğrulama işleridir.

## Değişmez Ürün ve Makale Sınırları

- v0.1 UI yalnız İngilizcedir; sonraki Türkçe/İtalyanca için string registry kullanılır.
- Runtime AI, analytics, login ve permanent project storage yoktur.
- Üç amaç Text Proximity, Group Comparison ve Style Over Time'dır.
- No-code vaadi yalnız desteklenen akışlarda önceden R/Python öğrenme veya kod yazma
  gereğini kaldırır; easy, intuitive, no knowledge needed veya universal usability denmez.
- Stability confidence değildir; Delta yazar tespiti kanıtı sunmaz.
- Pinokyo tool-first Style Over Time worked example'ıdır; ana edebiyat tezi değildir.
- PhiloEditor sürüm/varyant karşılaştırır; Delta independent-work stylometry yapar.
- Oğuz yöntem, claim ve acceptance sahibidir; AI ajanları implementasyon desteğidir.
- Barış ileride structured expert walkthrough yapar; bu bir participant user study değildir.

## P002 İçin Talimat

`prompts/P002-start.md` içindeki şablonu gerçek oturum isteğine uyarla. Önce yeni
P002 Ticket ve PromptEvent kaydı aç. Ardından yalnız roadmap'teki P002 shell
kapsamını uygula. Pazarlama landing page'i yapma; ilk ekran gerçek workbench olsun.
Henüz hesaplanmayan kontrolleri disabled ve açık etiketli tut. Ingestion, analiz
motoru, Pinokyo verisi, deployment veya runtime AI ekleme.

P002 kapanışı için desktop/mobile screenshot, keyboard accessibility, copy denylist
ve offline network trace kanıtları gerekir. Bir kapı geçmezse P002'yi complete yapma.

## Çalışma Ağacı ve Repo Notu

- Delta repository ayrı ve henüz remote'suzdur.
- Akademik-asistan kök repository'si `/delta.lemmata_app/` dizinini ignore eder.
- Kök çalışma ağacındaki Delta dışı kullanıcı değişikliklerine dokunma.
- P001 implementation commit'i temiz klon testinden geçti.

## P001 Kanıt Paketi

- `provenance/tickets/P001.json`
- `provenance/evidence/P001/report.md`
- `provenance/evidence/P001/environment-summary.json`
- `provenance/evidence/P001/clean-clone-verification.md`
- `provenance/runs/RUN-20260710-0001.json`
- `provenance/runs/RUN-20260710-0002.json`
- `decisions/ADR-0009-repository-and-environment.md`
- `memory/checkpoints/2026-07-10-p001-closed.md`
