# Delta Session Handoff

**Güncellendi:** 2026-07-11

**Aşama:** P002 denetimli olarak main'e alındı; P003 Secure Ingestion açıldı

**Kod durumu:** English-only workbench shell main üzerinde; secure ingestion henüz uygulanmadı, scientific computation yok

**Aktif ticket:** P003 Secure Ingestion (`in-progress`)

**Sıradaki tek ana iş:** P003 ingestion boundary ve malicious fixture testlerini uygula

## Önce Oku

1. `START_HERE.md`
2. Bu dosya
3. Roadmap'teki yalnız P003 bölümü
4. Claim CE-14
5. Threat SEC-01, SEC-02, SEC-03, SEC-04 ve SEC-05
6. `provenance/tickets/P003.json`
7. `prompts/P003-codex-execution-brief.md`
8. P003'ün etkileyeceği ingestion kodu ve malicious fixture testleri

## Uygulanan Bağımsız Denetim Talimatı

Claude Code'a yalnız şu mesaj gönderilir:

```text
prompts/P002-claude-independent-audit-and-repair.md dosyasını eksiksiz oku ve uygula. Önce hiçbir dosyayı değiştirmeden bağımsız çoklu-ajan denetimini tamamla; ardından yalnız kanıtlanmış P002 eksiklerini ayrı branch üzerinde düzelt, bütün test ve FAIR kapanış adımlarını çalıştır. Daha önce onaylanmış ürün kararlarını yeniden sorma; yalnız kanonik belgeler arasında çözülemeyen gerçek bir çelişki varsa dur.
```

Claude önce read-only altı mercekli denetim yapacak, sonra yalnız P002 içi kanıtlı
P0/P1 ve düşük riskli P2 bulgularını `claude/p002-independent-audit` branch'inde
düzeltecek. Main'e merge etmeyecek. Bulgular, before/after kanıtı, testler, clean
clone ve commit'ler Codex'in son denetimine bırakılacak.

## Claude Bağımsız Denetim Sonucu (2026-07-10, TAMAMLANDI)

- **Branch:** `claude/p002-independent-audit` (main'e merge EDİLMEDİ). Commit'ler:
  `0788a6e` (apply audit fixes) + review-evidence closure commit'i.
- **Hüküm:** kabul, 91/100. Açık P0/P1 = 0. Altı bağımsız mercek (product,
  visual/responsive, accessibility, python/streamlit, content/DH, security/FAIR).
- **Uygulanan (7):** sidebar aktif satır WCAG AA kontrastı (teal 2.5→6.3:1),
  kullanıcı metninden "P003" jargonu çıkarıldı, üç ölü accent token silindi,
  Guided/Research metni gelecek zamana çekildi, iki disabled butona help metni,
  paylaşımlı experiment-map helper, `runOnSave=false`.
- **Ertelenen (Codex/owner kararı):** kullanılmayan `pydantic` bağımlılığı,
  boundary-panel tekrarı (IA), önceki run/ticket provenance nitleri (SEC-1/3/4,
  eski kanıt değiştirilemez), P014 egress, ve P3 kuyruğu.
- **Kanıt:** `provenance/evidence/P002/claude-independent-review/` (report.md,
  findings.json, fix-matrix.md, before-after.md, browser-audit.json, smoke.json,
  contrast-proof.json, network-observations.json, clean-clone-verification.md,
  5 screenshot). Provenance: `PE-20260710-0004`, `RUN-20260710-0005/0006`,
  bağlı `HD-20260710-0005`. Eski P002 acceptance kanıtı değiştirilmedi.
- **Codex'e:** report.md "For Codex to re-examine" listesindeki 5 madde.

## Codex Düzeltme Sonucu (2026-07-11, MAIN'E ALINDI)

- **Branch:** `codex/p002-audit-corrections`, `8ef2582` merge commit'iyle main'e alındı.
- **Kod commit'leri:** `b53e3087` (arayüz, schema 1.1, replay/test altyapısı) ve
  `05e7b01c` (zoom kanıtını reflow ile sınırlayan düzeltme) ve `cd7d7b10`
  (Run artifact hash ve güvenli repository-path doğrulaması).
- **Düzeltilen merge engelleri:** P002 Ticket artık Claude/Codex PromptEvent,
  HumanDecision, Run, commit, ajan ve supplemental evidence bağlarını taşıyor;
  pathless `config_sha256` Run schema 1.1'de kaldırıldı ve eski anlam kayması
  additive errata + scoped supersession ile kaydedildi.
- **Arayüz:** mobil sidebar `auto`, bir `h1` + eş düzey `h2` yapısı, disabled
  nedenleri görünür ve düğme adlarında, P-ticket jargonu yok, yinelenen boundary
  paneli genel yöntem sınırına dönüştürüldü.
- **Doğrulama:** clean clone'da 47 test, yüzde 100 measured source coverage ve
  tüm kapılar geçti. Altı taze Playwright context'i masaüstü, mobil, 640px ve
  320px reflow, klavye, heading, disabled-state ve observed-request denetimini geçti.
- **Açıkça iddia edilmeyenler:** gerçek browser-chrome yüzde 200 zoom, manuel
  screen-reader conformance ve packet capture. Streamlit file-input/sidebar-toggle
  adları framework sınırı olarak kayıtlı.
- **Kanıt:** `provenance/evidence/P002/codex-correction/`,
  `RUN-20260711-0001/0002`, `PE-20260711-0001`, `HD-20260711-0001`.
- **Son denetim:** aynı bağımsız adversarial denetçi iki P2 düzeltmesini yeniden
  sınadı; açık P0/P1/P2 bulmadı ve `MERGE-READY` hükmü verdi.
- **Canlı ürün kapısı:** default, 390px ve 320px görünümler; üç research purpose,
  Research mode, Style Over Time sınırı, disabled durumlar ve konsol denetlendi.
  Açık P0/P1/P2 yok. Güvenilmez in-app raster kanıt olarak reddedildi.
- **Kullanıcı kararı:** `devam edelim` isteği, hemen önce açıklanan sıra kapsamında
  P002 main entegrasyonu ve ardından ayrı P003 açılışı olarak kabul edildi.
- **Main doğrulaması:** merge sonrasında 47 test, yüzde 100 measured source coverage,
  23 provenance kaydı ve tüm otomatik kapılar geçti.
- **Sonraki adım:** P003 secure ingestion implementation ve malicious fixture kapısı.

## P002 Sonucu

- Delta ilk ekranda doğrudan Streamlit workbench olarak açılıyor.
- Text Proximity, Group Comparison ve Style Over Time ilk sınıf research purpose.
- Guided ve Research shell seçenekleri var; çalışmayan sonraki aşamalar disabled.
- 94 user-facing string tek English registry içinde; language selector yok.
- Empty, loading, error, cancelled ve complete için ortak versioned contract var.
- Health/build bilgisi allowlist kullanıyor; path veya secret-shaped build ID reddediliyor.
- Runtime AI, analytics, login, permanent storage ve declared external endpoint yok.
- Desktop/mobile/reflow browser geometry, keyboard, copy denylist ve egress-denied testleri geçti.
- Otomatik doğrulama: 47 test, strict mypy, yüzde 100 measured source coverage.
- Implementation commit `a888e7c81e5fdae12687903de29d0728f5c7cbd5` yeni klonda yeniden kuruldu ve geçti.
- P002 Ticket; ilgili PromptEvent, HumanDecision, Run, commit, ajan, başarısızlık,
  errata ve supplemental evidence kayıtlarına makine-okur bağlarla bağlı.

## Doğrulanmamış Sınırlar

- Upload ve archive parsing henüz yok; P003'ün konusudur.
- Asset metadata, corpus inventory ve rights kararları P004'tür.
- Gerçek `stylo` execution/parity P006'dır.
- Upload-to-export no-code E2E henüz kurulmadı.
- Screen-reader ve tam WCAG conformance değerlendirmesi yapılmadı.
- Proxy/TLS/Host/CORS/CSRF/header ve shared-VPS isolation P014'tür.
- General usability veya ease claim'i yoktur.
- `lemmata.app` üzerinde `Launch Stylometry` bağlantısı eklenmedi; ayrı sonraki ticket'tır.

Bu maddeler gizlenmiş pass değildir. Claim ve threat kayıtlarında açık kalan kapı
olarak tutulur.

## Denetim Kabulünden Sonra P003

Codex, Claude branch'ini kabul ettikten sonra `prompts/P003-start.md` şablonunu
gerçek oturum isteğine uyarla. Önce P003 Ticket
ve PromptEvent aç. Sonra yalnız secure ingestion kapsamını uygula:

- `.txt`, `.zip` ve metadata `.csv`
- content-based type, UTF-8 ve Unicode NFC validation
- extraction öncesi archive member audit
- size, member count, ratio, path, nesting, token ve line limits
- server-generated asset ID ve escaped display filename
- CSV formula, HTML, newline, path ve log injection defenses
- content-free error code ve rejected-input cleanup

P003'te gerçek analysis, Pinokyo data, production deployment, parent-site launch
integration, PDF/DOCX/EPUB/TEI veya OCR ekleme. Bir malicious fixture kapısı
geçmezse P003'ü complete yapma.

## FAIR Kapanış Disiplini

Her ticket açılışında PromptEvent, Ticket ve gerekiyorsa HumanDecision kaydı açılır.
Her ara başarısızlık acceptance raporunda korunur. Kapanışta komutlar, Run, claim,
threat, screenshots/fixtures ve clean-clone sonucu bağlanır. Summary-only kayıt
native transcript gibi sunulmaz ve `FAIR-certified` dili kullanılmaz.

## P002 Kanıt Paketi

- `provenance/tickets/P002.json`
- `provenance/evidence/P002/report.md`
- `provenance/evidence/P002/browser-audit.json`
- `provenance/evidence/P002/accessibility-report.json`
- `provenance/evidence/P002/network-trace.json`
- `provenance/evidence/P002/copy-snapshot.txt`
- `provenance/evidence/P002/clean-clone-verification.md`
- `provenance/runs/RUN-20260710-0003.json`
- `provenance/runs/RUN-20260710-0004.json`

## Repository Notu

- Delta ayrı, remote'suz `main` repository'sidir.
- Parent akademik-asistan repository'si Delta dizinini ignore eder.
- Parent çalışma ağacındaki Delta dışı kullanıcı değişikliklerine dokunma.
