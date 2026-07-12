# P004 Lemmata Family Palette and Parameters Checkpoint

**Tarih:** 2026-07-12

## Karar

- Delta, Lemmata ürün ailesinin canlı görsel diline bağlandı: koyu yeşil eylem,
  açık gri çalışma alanı, açık gri sidebar ve soft mint öğretici yüzeyler.
- `Current boundary` geliştirici metni kaldırıldı. Sidebar artık `Start here`, üç
  işlem adımı, parametre sıralaması ve collapsed `Technical status` gösteriyor.
- Guided Mode 100/300/500/1000 MFW dener; 500 MFW, yüzde 0 culling, whole text ve
  Classic Delta yalnız sabit referanstır, en iyi ayar değildir.
- Research Mode gelecekte MFW, culling, segmentation ve distance için sınırlandırılmış
  kontroller sunacak; public job en çok 24 belgeli kombinasyon çalıştıracak.
- Kontroller P006/P007/P008 motor ve corpus-health kapıları tamamlanmadan açılmadı.

## Kanıt

- Brief: `prompts/P004-family-palette-and-parameter-orientation.md`
- Rapor:
  `provenance/evidence/P004/family-palette-parameter-orientation-validation.md`
- İlk browser denemesi placement ve mobil-oracle nedeniyle fail olarak saklandı.
- İkinci browser denemesi altı viewport, TXT/ZIP, computed palette, kontrast,
  no-overflow, no-egress ve clean-console kapılarında geçti.
- `./scripts/verify.sh` ilk formatting failure sonrasında 468 test, 3.171 statement,
  880 branch ve yüzde 100 coverage ile geçti.
- Exact implementation commit `54e479d`, `RUN-20260712-0003` ile fresh
  no-hardlinks detached clone'da bootstrap, full gate ve aynı browser audit'ten
  geçti; clone temiz kaldı.
- Provenance-link commit `5d95ce4`, GitHub CI run `29201459098` içinde Linux
  verify, SBOM/dependency audit ve amd64 container build işlerinde geçti.

## Sınır

Exact `research-grid-v1`, izin verilen segmentler, kaynak limitleri ve stability
eşikleri henüz dondurulmadı. Scientific analysis, AI, storage, deployment ve P004
insan kabulü eklenmedi.
