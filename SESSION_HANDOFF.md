# Delta Session Handoff

**Güncellendi:** 2026-07-10

**Aşama:** P002 tamamlandı; P003 Secure Ingestion başlamaya hazır

**Kod durumu:** English-only workbench shell doğrulandı; ingestion ve scientific computation yok

**Aktif ticket:** Yok

**Sıradaki tek ana iş:** P003 Secure Ingestion

## Önce Oku

1. `START_HERE.md`
2. Bu dosya
3. Roadmap'teki yalnız P003 bölümü
4. Claim CE-14
5. Threat SEC-01, SEC-02, SEC-03, SEC-04 ve SEC-05
6. `provenance/tickets/P002.json`
7. `provenance/evidence/P002/report.md`
8. `provenance/evidence/P002/clean-clone-verification.md`

## P002 Sonucu

- Delta ilk ekranda doğrudan Streamlit workbench olarak açılıyor.
- Text Proximity, Group Comparison ve Style Over Time ilk sınıf research purpose.
- Guided ve Research shell seçenekleri var; çalışmayan sonraki aşamalar disabled.
- 90 user-facing string tek English registry içinde; language selector yok.
- Empty, loading, error, cancelled ve complete için ortak versioned contract var.
- Health/build bilgisi allowlist kullanıyor; path veya secret-shaped build ID reddediliyor.
- Runtime AI, analytics, login, permanent storage ve declared external endpoint yok.
- Desktop/mobile browser geometry, keyboard, copy denylist ve egress-denied testleri geçti.
- Otomatik doğrulama: 40 test, strict mypy, yüzde 100 measured source coverage.
- Implementation commit `a888e7c81e5fdae12687903de29d0728f5c7cbd5` yeni klonda yeniden kuruldu ve geçti.
- P002 Ticket, PromptEvent, iki HumanDecision, iki Run ve sekiz başarısızlık/düzeltme izi bağlı.

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

## P003 İçin Talimat

`prompts/P003-start.md` şablonunu gerçek oturum isteğine uyarla. Önce P003 Ticket
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
