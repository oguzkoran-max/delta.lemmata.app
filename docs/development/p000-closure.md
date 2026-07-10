# P000 Closure Record

**Ticket:** P000  
**Başlık:** Pre-development contract, evidence architecture, and agent handoff  
**Durum:** Complete  
**Kapanış tarihi:** 2026-07-10  
**Son ek:** 2026-07-10, scholarly vibe coding ve no-prior-Python clarification  
**Ürün kodu:** Yazılmadı

## 1. Kapanış Kararı

P000 tamamlanmıştır. Kullanıcı kararı gerektiren ürün, makale, Pinokyo, PhiloEditor, runtime AI, değerlendirme, yazarlık veya yayın takvimi bloklayıcısı kalmamıştır. Henüz yanıtlanmamış sayısal ve ampirik konular yanlış biçimde “karar” sayılmamış, ilgili P-ticket acceptance kapılarına taşınmıştır.

P001 başlamaya hazırdır. P001 geçmeden P002 veya başka ürün özelliğine başlanmaz.

### Kapanış Sonrası Açıklık Eki

Kullanıcı, “Python öğrenmeden” boyutunun yalnız son kullanıcı için değil kendi geliştirme deneyimi için de merkezi olduğunu açıkladı. Bu yeni bir ürün özelliği açmadı; mevcut no-code ve AI provenance kararını keskinleştirdi. ADR-0008 ile scholarly vibe coding tanımlandı, CE-20 eklendi ve P001 provenance kapsamına HumanDecision ledger alındı. Repository topolojisi ADR numarası ADR-0009'a taşındı.

## 2. Üretilen Kanonik Paket

| Alan | Artifact | Kapanış ölçütü |
|---|---|---|
| Ürün, yöntem, FAIR, güvenlik ve makale sözleşmesi | `DEVELOPMENT_CONTRACT.md` | Kanonik kapsam ve karar hiyerarşisi var |
| Uzun ömürlü proje hafızası | `PROJECT_MEMORY.md` | Onaylar, gerekçeler, reddedilen yollar ve açık kanıt işleri var |
| Aktif devir | `SESSION_HANDOFF.md` | Sıradaki tek iş P001 olarak tanımlı |
| Hızlı ajan yönlendirmesi | `START_HERE.md` | Minimum aktif-ticket okuma yolu var |
| Mimari ve yöntem kararları | `decisions/ADR-0001` ile `ADR-0008` | Kabul edilmiş karar ve sonuç kayıtları var |
| Claim planı | `docs/research/claim-evidence-matrix.md` | 20 claim, test kapısı, artifact, fallback ve denylist var |
| Tehdit modeli | `docs/security/threat-model.md` | Güvenlik, hak/FAIR ve epistemik riskler release kapılarına bağlı |
| Environment politikası | `docs/development/supported-environments.md` | Canonical, CI, production, clean rerun, Mac ve browser rolleri ayrılmış |
| Pinokyo protokolü | `docs/methodology/pinocchio-diachronic-worked-example.md` | Diachronic worked example, confound ve rights gate tanımlı |
| Geliştirme planı | `docs/development/roadmap-P001-P015.md` | Bağımlılık grafiği, acceptance, kanıt, non-goal ve zamanlama var |
| Claude/Codex adaptörleri | `CLAUDE.md`, `AGENTS.md` | Agent-nötr sözleşmeye ve aktif ticket'a yönlendirir |
| P001 geçiş mesajı | `prompts/P001-start.md` | Şablon olduğu ve henüz native PromptEvent sayılmadığı açık |

## 3. P000'da Dondurulan Ana Kararlar

- Delta, scholar-led ve no-code stilometri workbench'idir; yeni metrik iddia etmez.
- Desteklenen akışlara başlamak için önce R/Python öğrenmek veya kod yazmak gerekmez. Bu, genel ease, usability, teachability veya yöntem bilgisine gerek olmadığı claim'i değildir.
- Oğuz formal Python yazılım geliştirme uzmanlığı olmadan Delta'yı Claude ve Codex ile geliştirir; bu scholar-led, evidence-gated yöntem scholarly vibe coding olarak kaydedilir.
- Scholarly vibe coding ana tool tezinin yerine geçmez ve programlama uzmanlığının gereksizliği şeklinde genellenmez.
- R `stylo` kanonik motor, Python/Streamlit orchestration ve UI katmanıdır.
- v0.1 yalnız İngilizce UI kullanır; runtime AI, login, analytics ve permanent storage içermez.
- Text Proximity, Group Comparison ve Style Over Time birinci sınıf amaçlardır.
- Parameter stability, confidence değildir; eşikler benchmark üzerinde kalibre edilmeden etiket yayımlanmaz.
- Public Research Mode 24 sürümlü hücre, controlled publication batch en çok 192 hücre kullanır.
- Pinokyo, authorship veya iki-redaksiyon karşılaştırması değil, Collodi diachronic worked example'ıdır.
- Delta; PhiloEditor'ın diff, alignment, variant annotation veya critical edition görevini tekrar etmez.
- Asset-level rights, default raw-free export, süreli retention ve tested VPS isolation zorunludur.
- Oğuz geliştirir ve birinci/sorumlu yazardır; Barış structured expert walkthrough yapar ve ikinci yazardır.
- Katılımcılı user study yoktur; AI ajanları yazar değildir.
- Hedef Umanistica Digitale ve Şubat 2027'dir; kanıt kapıları takvimden üstündür.

## 4. Multi-Agent P000 Denetimi

P000 son denetimi toplam 75.000 token tavanlı üç paralel rol olarak yürütülmüştür; rol başına 25.000 token ayrılmıştır.

| Rol | Sonuç | P000'a etkisi |
|---|---|---|
| Claim-evidence reviewer | Tamamlandı | İlk 19 claim, fallback dili, denylist ve `reproducible` embargo kuralı; kullanıcı açıklığı sonrası CE-20 ayrıca eklendi |
| Security/rights/epistemic reviewer | Tamamlandı | Threat ID'leri ve üç release kapısı |
| Ticket-roadmap reviewer | Bütçeyi başlangıç belgelerini okuyarak tüketti; kullanılabilir rapor üretmedi | Başarısızlık saklanmadı; roadmap yerel sentezlendi ve `START_HERE.md` aktif-ticket yönlendirmesi eklendi |

Bu kayıt P001 öncesi `summary-only` provenance'dır. Native agent prompt/response export'u varmış gibi sunulmaz. P001'den itibaren PromptEvent şeması kullanılır.

## 5. Sonraki Ticket'lara Taşınan Kanıt İşleri

| Açık kanıt | Ticket | Neden P000 bloklayıcısı değil? |
|---|---|---|
| Exact Python/R/package/container sürümleri | P001 | Tasarım değil, kurulum ve lock kanıtı gerektirir |
| Secure upload limitleri | P003, P014 | Fixture ve load testi olmadan sayısallaştırılamaz |
| Collodi asset-level source/edition/rights audit | P004, P013 | Varlık düzeyinde kaynak incelemesi gerekir |
| `research-grid-v1` kesin 24 hücresi | P010, P011 | Benchmark öncesi protokol ve kaynak ölçümü gerekir |
| Stability eşikleri veya raw-only fallback | P010, P011 | Calibration ve locked test kanıtı gerekir |
| Reproducibility seviyesi ve clean rerun | P012, P015 | Gerçek package ve ikinci ortam koşumu gerekir |
| VPS kaynak sınırları ve Lemmata etkisi | P014 | Production-benzeri load ve isolation testi gerekir |
| Barış acceptance sonucu | P015 | Çalışan v0.1 üzerinde structured walkthrough gerekir |

## 6. Claim Embargosu

P000 bir tasarım ve kanıt planı üretmiştir; ürün davranışını ampirik olarak doğrulamamıştır. Bu nedenle:

- `Reproducible` başlık veya güçlü ana claim'de CE-11 ve CE-12 birlikte geçmeden kullanılmaz.
- Stability label'ları CE-08 geçmeden release edilmez.
- “Easy”, “usable by general researchers”, “teachable”, “finds the author” ve benzeri denylist dili kullanılmaz.
- P000 belgeleri product validation evidence olarak sayılmaz.

## 7. Mekanik Doğrulama

P000 belge paketi proje kökünden şu kontrollerle doğrulandı:

| Kontrol | Komut özeti | Gerçek sonuç |
|---|---|---|
| Markdown yapı | `find` + `awk` ile active `.md` dosyalarında H1 ve fence sayımı | Her dosyada tek H1; backtick/tilde fence dengeli |
| Eski durum ve vaat | `rg` ile eski P000 active-stage, eski başlık ve sınırlandırılmamış eski tagline | Aktif belgelerde sıfır stale ifade; yeni bounded no-prior-code vaadi korunur |
| Türkçe tipografi | `rg` ile Unicode U+2014 taraması | Aktif Delta ve wiki sayfasında sıfır em dash |
| Yerel yol ve secret | `rg` ile local absolute path, file URI ve API-key pattern taraması | Sıfır eşleşme |
| Kanonik hedefler | `test -f` ile contract, ADR-0001..0007, claim, threat, roadmap, environment, prompt ve checkpoint | Bütün hedefler mevcut |
| Kimlik kapsamı | `rg`, `sort -u`, `wc -l` | 20 CE, 16 SEC, 9 RP, 13 EPI, 15 P-ticket |
| Cross-reference | `comm` ile roadmap claim/threat ID'leri kaynak listelerine karşı | Eksik ID sıfır |

P000 yalnız belge ve karar ticket'ıdır. Ürün kodu, runtime veya bilimsel run bulunmadığı için uygulama testi çalıştırılmadı ve çalıştırılmış gibi kaydedilmedi.

## 8. Kapanış Kontrolü

- [x] Kullanıcı tarafından onaylanmış kararlar kanonik belgelerde kayıtlı.
- [x] P000 kullanıcı bloklayıcısı sıfır.
- [x] Claim-evidence matrix var.
- [x] Security, rights/FAIR ve epistemic threat model var.
- [x] Supported environment matrix var.
- [x] Pinokyo ve PhiloEditor görev sınırı var.
- [x] P001-P015 bağımlılık ve acceptance planı var.
- [x] Claude ve Codex için aynı kanonik kaynağa yönlendiren başlangıç yolu var.
- [x] Scholarly vibe coding sorumluluk ayrımı ve HumanDecision provenance planı var.
- [x] P001 prompt template, native kayıt olmadığı açıkça belirtilerek hazır.
- [x] Ürün kodu yazılmadı.
- [x] Aktif belgelerde P000/P001 durumu, stale claim dili, link hedefleri ve Markdown bütünlüğü kontrol edildi.

## 9. Sıradaki Tek İş

`prompts/P001-start.md` şablonunu gerçek P001 oturumunda kullan. Önce PromptEvent, Ticket ve HumanDecision kayıtlarını aç, ardından yalnız repository, lock, metadata ve provenance scaffold kapsamını uygula.
