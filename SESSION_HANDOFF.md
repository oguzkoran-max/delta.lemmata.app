# Delta Session Handoff

**Güncellendi:** 2026-07-18

**En yeni checkpoint: Pre-manuscript public-alpha denetimi + düzeltmeler + Codex
R1 (draft PR #15, unmerged).** Claude Code, canlı public-alpha'yı makale öncesi
yedi bağımsız mercek + adversaryel sentezle denetledi. `claude/p014-pre-manuscript-audit`
dalı origin/main `3cfe0713`'ten açıldı. Bağımsız Codex incelemesi sonrası
düzeltilmiş sonuç: **P0=0, P1=0, P2=3 (2 fix + 1 makale-açığı), P3=7, +1
savunma-derinliği (uygulandı)**; karar **CONDITIONAL GO** (yalnız "makale
tasarımına başlanabilir mi?"; P011-P015 açık, gönderim-hazır iddiası yok).

Düzeltilen (test eklenerek, canlıya deploy YOK): (1) **P2 BARIS-INTAKE-01** —
Barış canlıda `INGEST_INVALID_UTF8` alıp app'i takılmış sanıp yeniledi (repro:
yenilemeye gerek yok). Neden-özel mesaj (UTF-8/markup) + **hata-sınıfına duyarlı**
yönlendirme (kurtarılabilir → "başka dosya, yenileme yok"; iç/sistem hatası →
"sistem hatası, sürerse yenile" — Codex R1). (2) **P2 UI-METRIC-TRUNC-01** —
Parameters özet metrikleri masaüstünde "500 MF…"/"Whole t…" kırpıyordu; `ui_theme`
wrap kuralı (375×844 dahil doğrulandı). (3) **Savunma-derinliği SEC-XFF-01** —
Codex R1: Caddy varsayılanı istemci-verili XFF'i zaten yok sayar (boş
`trusted_proxies`), yani P1 "vulnerability" DEĞİLDİ; açık `header_up X-Forwarded-For
{http.request.remote.host}` pin'i savunma-derinliği olarak korundu +
validator/test/README savunma-derinliği diline çekildi. **Owner canlı Caddyfile'da
geniş `trusted_proxies` olmadığını + pin'i teyit etmeli.**

Ertelenen: FAIR-PKG (P012), VIS-RAIL (owner görsel), A11Y-HEADING (owner görsel),
CODE-DEAD-STRINGS, 4 makale-açığı (P011/P012/P013/P015). Rapor:
`provenance/evidence/P014/pre-manuscript-public-alpha-audit.md`; kanıt +
önce/sonra + görünür red-mesajı + 375 metrik görselleri (SHA manifesti)
`provenance/evidence/P014/pre-manuscript-audit/`.

Uygulama (kod) final SHA `22e3e1d`; kanıt/rapor SHA bunun üstündeki doc commit'i
(bilinçli ayrı). Yerel `./scripts/verify.sh` geçti (1738 passed, 1 skip, %100
coverage, records-ok=119, verify-ok); taze-klon kaynak testi geçti. Canonical
Linux CI draft PR #15'te koşar (ilk turda belgeli aralıklı P009 result-selector
harness flake'i çıktı; identik push geçti, re-run yeşil). Bu kapanış
merge/deployment/public-activation DEĞİLDİR; owner + Codex review bekler. Canlı
Delta ve LDA sağlıklı, dokunulmadı.

---

**En yeni checkpoint: Phase B main image publication.** Claude Code'un
owner-selected A5.1 prototip sistemiyle kapanan Phase B, PR #8 üzerinden normal
merge commit `25fc2cadbba2147db6c7767e802088706a305f28` olarak `main`e alındı.
Exact-main CI `29597139461` verify `87940183844` ve container `87940183862`
işlerinde geçti. Publication run `29597615330`, job `87941738365`, aynı source'u
yeniden build edip hardened stack gate'ten geçirdi ve yalnız exact-commit tag'i
yayımladı.

Güncel private deployment identity:
`ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:eb0c13a77dc39af8cf4dbfdadc811dd3bbe1f0b3d0381b15e140f5367ce9a54d`.
`latest` yayımlanmadı. Exact tag yalnız locator'dır; deployment digest ile
yapılır ve target hostta doğrulanır. İmaj signed/attested değildir. Kanıt
`provenance/evidence/P014/phase-b-main-immutable-image-publication.md`, run
`RUN-20260717-0003`, checkpoint
`memory/checkpoints/2026-07-17-p014-main-image-publication.md` içindedir.

Önceki exact closure implementation'i
`d637893a19cc33e57b8826c5ff8625bd196cb1d4` ve onun retained kanıt zinciri
değişmeden korunur.

Final exact commit'te push CI `29592151976` verify `87923605718` ve container
`87923605615`; PR CI `29592158057` verify `87923626171` ve container
`87923628578` işleri geçti. Canonical Linux 1.726 test, 11.692 statement,
3.050 branch ve yüzde 100 measured coverage bildirdi. Browser audit temiz Git,
canonical worker, distinct-owner predecessor izolasyonu, tek-en-eski FIFO işi,
exact-job sonuç görünümü, terminal payload cleanup, responsive viewport,
native-keyboard result selection, semantic tables/charts ve export kapılarından
geçti. İçeriksiz JSON SHA-256:
`e2508e6152abd7a639323c6af47d69b29dae7affad3973709b645c65fc911578`.

Üç bağımsız exact-SHA bilimsel-yöntem, erişilebilirlik ve FAIR/privacy/lifecycle
denetimi P0-P3 açık bulgu bırakmadan yalnız Phase B kod ve otomatik kanıt
kapanışına `GO` verdi. `7585d83`, `8198dd82`, `a5b94d5`, `dfce029` ve
`8c813ff` aşamalarındaki failure, conditional ve NO-GO kanıtları silinmeden
korunur. Superseding kayıt `RUN-20260717-0002`; ana belge
`provenance/evidence/P014/phase-b-review-remediation.md`; exact artefaktlar
`provenance/evidence/P014/phase-b-exact-d637893/` altındadır.

Bu kapanış GitHub review'u, katılımcı testi, manual VoiceOver/NVDA doğrulaması,
owner activation kabulü, FAIR completeness, benchmark doğruluğu, genel usability
veya public deployment değildir. P011 sensitivity, tam P012 FAIR paketi,
Pinokyo çalışması ve P014 host kapıları açık sınırdır.

**Güncel operasyon kararı:** Oğuz `HD-20260717-0001` ile normal merge, exact-main
CI, immutable image publication ve localhost-only host staging sırasını kabul
etti. Merge, publication, evidence PR #9 ve main CI tamamlandı. Fresh live
`pre-docker` gate'i geçti; ilk official-Docker installer dispatch'i, o sıradaki
runbook `pre-mutation` kanıtını verirken installer doğru biçimde `pre-docker`
baseline'ı istediği için mutasyondan önce
`P014_DOCKER_INSTALL_GATE_PHASE_INVALID` ile durdu. Post-failure read-only
recheck Docker binary/package/key/source/data root veya transaction directory
bulmadı; Caddy ve Lemmata active, `8502` kapalı ve Caddyfile hash'i değişmemişti.
Failed run `RUN-20260717-0004`, raw gate JSON'ları
`provenance/evidence/P014/live-20260717/`, açıklama
`docker-install-preflight-contract-failure-20260717.md` içindedir. Installer
değişmez; runbook, validator ve test düzeltmesi normal review/CI'dan geçtikten
sonra official Docker hazırlığı yeni bir Run olarak yeniden uygulanır. External
denial ve değişmemiş Lemmata kanıtı Oğuz'a gösterilmeden Caddy, DNS veya public
route değişmez. P014 `in-progress`; AC-05 ile AC-08-AC-10 pending kalır.

**Tarihsel ve genel aşama özeti:** P001-P006 tamamlandı. P007 teknik kapılardan geçti; bütünleşik son
owner walkthrough'u açıktır. P008'in dört hücreli Guided minimum-alpha yolu ve
P009'un export-backed sonuç/yorum sınırı yüzeyi gerçek R/stylo worker,
desktop/mobile/reflow browser, remote clean-clone ve canonical Linux CI
kapılarından geçti. P007-P009, tam üç amaç ve ilgili known/unknown browser
matrisi, owner walkthrough ve tam görsel/glossary genişletmesi için ertelenmiş
`blocked` kalır. Minimum P014
deployment paketi canonical Linux CI'da geçti; gerçek host inventory,
coexistence/load, restart/rollback ve owner acceptance kapıları açıktır.
İlk read-only host preflight'i Lemmata'yı sağlıklı ve `8502`yi boş buldu, fakat
hostta container runtime olmadığı için kurulumdan önce fail-closed durdu. Exact
green main image'ı private GHCR'da immutable digest ile yayımlandı; canlı VPS
henüz değiştirilmedi. İkinci read-only gözlem Docker'ın host networking etkisi ve
dar memory margin'i doğruladı. Oğuz `HD-20260715-0002` ile ADR-0018'in aynı VPS,
official Docker ve yeni swap oluşturmama profilini ordered host preparation ve
measurement için kabul etti. İlk pre-execution audit faz sırası, runtime-absent
inventory, exact install/rollback ve ayrı pre-Caddy gate açıklarını buldu. Bunları
kapatan deterministic host/load gate, Docker installer/rollback ve runbook değişikliği
`codex/p014-live-host-acceptance` dalında önce hedefli 42 testten ve full local
verify kapısından geçti.
Sonraki iki focused adversarial review optimized-assert, mutate-before-current-
validation, rollback-stop, first-release cleanup, image revision, exact candidate
origin ve closed real-analysis load açıkları nedeniyle yeniden `NO-GO` verdi.
Birleşik remediation schema `1.3.0` pre-mutation/origin/key, erken cleanup,
partial-install rollback, image revision ve sustained real R/`stylo` load
kapılarını tamamladı. Güncel host paketi 109 focused testten geçti. Son browser
harness düzeltmesiyle ilgili paket 121 testten ve full verify'da 1.656 pass, bir
canonical Linux skip ve yüzde 100 measured coverage kapısından geçti.
Karar üretmeden bütçesini tüketen ajan turları approval sayılmadı. Canlı VPS
değiştirilmedi. Draft PR #7'de ilk iki Linux run'ı hermetik olmayan absent-Docker
testini buldu; düzeltme commit'i `11a440b` için push CI `29484009945` ve PR CI
`29484013488` verify/container işlerinde yeşildir. Kanıt commit'i `5c1b083` için
push CI `29484671596` yeşil, PR CI `29484673782` ise ikinci result export
indirmesi Streamlit rerun'ıyla çakışıp `Download.path: canceled` verdiği için
yalnız browser adımında kırmızıdır. Kaynak/test ve container kapıları geçti.
`268c525` bu indirme düzeltmesini taşıdı. PR CI `29486381721` tamamen geçti; eş
push CI `29486378477` bilimsel sonuç hazır olduktan sonra eski zorla-tıkla/`fill`
selectbox yolunda takıldı. Working tree indirme öncesinde bağlı ve kararlı-idle
Streamlit durumunu iki kez doğrular, gerçek download failure için retry yapmaz ve
sonuç seçicisini erişilebilir `combobox`/`option` rolleriyle işletir. Bu düzeltmenin
`5d57f14` exact head push CI `29487643303` koşumu tamamen geçti. Paralel PR CI
`29487646240` hardened container, gerçek R/`stylo`, sonuç yüzeyi, grafik ve export
kapılarını geçti; yalnız kapasite tablosunu dört satırı görünmeden okuyan harness
iki preparation oracle'ını false kaydetti. Working tree dört satırı bekler, iki
kararlı snapshot şartı koyar ve satırları kanıta ekler. Yedi helper, 159 ilgili
test ve full verify'da 1.658 pass, bir canonical Linux skip ve yüzde 100 measured
coverage geçti. Bu tarihsel bekleme PR #7'nin normal merge commit'i
`26947e1f6843b2b4dc1d1b0cc552c0af808be3fa` ile tamamlandı; canlı host
değiştirilmedi.

**Kod durumu:** P004 guided corpus akışına ek olarak P005'te versioned lifecycle,
256-bit session/job identity, payload-free atomic SQLite queue, private workspace,
validated-payload staging, capability-first application service, synthetic POSIX
process controller, kalıcı content-free deletion ledger, continuous fake-clock
janitor, ayrı app-loss guardian, durable SQLite terminal ACK ve execution-bound
recovery receipt var. P006 kapalı input/result/fatal-error şemaları, strict tek-parse
parser, input-dependent semantic validator, process sonucundan ayrı saf scientific
finalizer, bounded no-follow workspace read, fixed R worker, shell-free adapter,
checksum-frozen direct-`stylo` oracle, retained worker package ve crash-safe
scientific-result handoff var. P007'de deterministic preparation, purpose-aware
confound warnings, exact/near/shared-passage kontrolleri, READY/BLOCKED kararı,
beş semantic-table-bound diagnostic panel ve dört content-free CSV bağlıdır.
P008'de kapalı Guided parameter resolution, review-before-run, one-time READY
admission ve gerçek P006 analysis orchestration bağlıdır. P009'da dört hücreli
sonuç görünümü, sabit 500-MFW reading reference, distance heatmap, exact-tie
nearest-neighbor tablosu, deterministic MDS haritası, semantic table parity,
claim lint ve raw-text-free result export bağlıdır. P014'te versioned,
loopback-only, egress-denied ve hardened public-alpha stack paketi vardır; canlı
VPS kurulumu veya public route yoktur. Benchmark, calibrated stability, tam FAIR
run package ve Pinokyo çalışması hâlâ yok.

**Son tam kapanan ticket:** `provenance/tickets/P006.json` (`complete`)

**Aktif implementation ticket:** `provenance/tickets/P014.json` (`in-progress`;
AC-01 ile AC-04 ve AC-06 ile AC-07 passed, AC-05 ile host-bound AC-08 ile
AC-10 pending)

**Sıradaki tek ana iş:**
`RUN-20260717-0004` ile tutulan preflight-contract failure düzeltmesini normal
review ve yeşil CI ile birleştir; ardından installer'a accepted `pre-docker`
baseline'ı vererek guarded official-Docker preparation ve localhost-only kurulumu
yeni Run olarak yap. Pre-Caddy evidence review tamamlanmadan public route açma.

**Claude Code kesin devam noktası:** Önce `START_HERE.md`, sonra bu dosya,
`deploy/public-alpha/README.md`,
`provenance/evidence/P014/phase-b-main-immutable-image-publication.md`,
`provenance/runs/RUN-20260717-0003.json` ve
`memory/checkpoints/2026-07-17-p014-main-image-publication.md`; ardından
`provenance/evidence/P014/docker-install-preflight-contract-failure-20260717.md`,
`provenance/runs/RUN-20260717-0004.json` ve
`memory/checkpoints/2026-07-17-p014-host-preflight-contract-correction.md` okunur. Kalıcı
tasarım kaynağı ve önceki exact review artefaktları değiştirilmeden korunur.
Canlı işlem sırası runbook'tur; pre-Caddy owner gate atlanmaz.

**P014 canonical package checkpoint'i:** Exact implementation commit'i
`7f26dbe82437e7f9757e7c35b10b7666a3078578`; run kaydı
`RUN-20260715-0004`; canonical Linux CI `29420509541` içinde verify job
`87369452370` ve container job `87369452318` yeşildir. CI'da 1.564 test, 11.382
statement, 2.964 branch ve yüzde 100 measured coverage; gerçek R/stylo browser
akışı; SBOM/dependency/secret; canonical image; hardened stack; TLS, strict Host,
tek başarılı WebSocket; desktop/mobile/320px reflow; denied egress; hostile
requests; runtime inspection ve cleanup geçti. App image ID
`sha256:f96fbd196c1e71b86a3dde8254f70fca3c2ff3d69306a4f6e02be73cb69a9934`;
pinned gateway manifest digest
`sha256:3b24c4bfb2b9f60359b1475605ca1c8ed6e4963eb8369c6835be4d96bdb3ea81`.
On iki başarısız veya superseded CI outcome nedenleriyle korunur. Kanıt:
`provenance/evidence/P014/canonical-alpha-stack-validation.md`. Registry manifest
digest artık kayıtlıdır; accepted post-preparation host inventory, live TLS,
Lemmata load, restart/rollback ve owner kabulü henüz yoktur; public activation
yasaktır.

**P014 target-host preflight checkpoint'i:** Kanıt-link commit'i
`dea9e67154d75852c5d69db9871fd4a1868bc236`, PR CI `29424064991` içinde verify ve
container işlerinde yeşildir. Read-only host run'ı `RUN-20260715-0005` exit `21`
ile fail-closed oldu. Ubuntu 26.04 x86_64 hostta 2 CPU, 3.814 MiB RAM, 2.360 MiB
available RAM, sıfır swap ve 32.621 MiB boş root disk gözlendi. Docker, Podman,
containerd ve nerdctl yoktur. Caddy ve Lemmata active; Lemmata yaklaşık 1,04 GiB
kullanır ve finite CPU/RAM cap'i yoktur; `8501` dinler, `8502` boştur. Public
Lemmata health `ok`; 20 sequential request 20/20 HTTP 200, median 182,02 ms ve
p95 267,73 ms verdi. Hiçbir paket, swap, service, Caddy, DNS veya dosya değişikliği
yapılmadı. Kanıt: `provenance/evidence/P014/target-host-read-only-preflight.md`.
Bu failed preflight AC-08'i kapatmaz; accepted post-preparation inventory,
container-runtime/capacity kararı ve bütün host-bound kapılar pending'dir.

**P014 immutable image checkpoint'i:** PR #4 normal merge commit
`8579e4e335cfa3ccbd1368588bf11d60dca08764` ile commit geçmişini koruyarak
`main`e alındı. Main CI `29426588836` içinde verify `87390451573` ve container
`87390451645` geçti. Publication run `29426974523`, job `87391795653`, exact
source'u yeniden build edip hardened stack, TLS browser, denied-egress ve cleanup
kapılarını tekrar geçirdi. Local image ID
`sha256:d03752691358a8aeb9387f90f97523c5779ecded0e63f8dc1d463b9fa5cddacf`;
private deployment reference
`ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:596591039de86c39c976f984b5b22fc3fc040bd56a08c471cbb349aa6c84b4a2`.
`latest` etiketi yayımlanmadı. Kayıt: `RUN-20260715-0006` ve
`provenance/evidence/P014/immutable-image-publication.md`. Bu image publication
canlı host readiness veya activation kanıtı değildir.

**P014 runtime/capacity checkpoint'i:** Immutable publication kanıtı PR #5 ile
normal merge commit `cc44132b524ae31e052a3af69ad4c416c88a223c` üzerinden
`main`e alındı; main CI `29429031944` verify ve hardened-container işlerinde
yeşildir. `RUN-20260715-0007` read-only gözleminde Ubuntu 26.04 x86_64, cgroup v2
`cpu`/`memory`/`pids`, 2.357 MiB available RAM, sıfır swap, sıfır firewall rule,
disabled forwarding, sıfır memory pressure, healthy zero-restart Lemmata ve boş
`8502` doğrulandı. Hiçbir host değişikliği yapılmadı. ADR-0018 mevcut VPS üzerinde
official Docker, yeni disk swap'i oluşturmama, Delta swap denial'ını koruma,
Lemmata p95 artışı için frozen yüzde 20 budget ve açık memory/OOM/network stop
kapılarını tanımlar. Oğuz `HD-20260715-0002` ile yalnız ordered host preparation
ve measurement kapsamını kabul etti; deterministic host-command review ve
separate pre-Caddy owner gate zorunludur. Kanıt:
`provenance/evidence/P014/target-host-runtime-capacity-observation.md`.

**P009 minimum-alpha checkpoint'i:** Exact implementation commit'i
`c5e39b07bb65a11613684a10269b186c987ef980`; run kaydı
`RUN-20260715-0003`; canonical Linux CI `29402396790` içinde 1.523 test, gerçek
upload-to-public-result Playwright akışı, iki nonblank chart, iki result download,
desktop/mobile/320px reflow, payload canary, console/network,
SBOM/dependency/secret ve Linux amd64 container kapıları geçti. Yerel ve private
remote clean-clone turu 1.522 test, bir documented macOS Linux-only skip ve yüzde
100 measured coverage ile geçti; clone temiz kaldı. Kanıt-link commit'i
`567d154e697609996e514447ab116f5532c1704d`, CI `29404000108` içinde verify ve
container işlerinde yeniden yeşildir. Yedi önceki CI failure nedenleriyle birlikte
korunur. Kanıt: `provenance/evidence/P009/minimum-alpha-results-validation.md`.

**P008 minimum-alpha checkpoint'i:** Guided Mode tam olarak 100, 300, 500 ve
1000 MFW; yüzde 0 culling; whole text; Classic Delta; seed 20260713 ve optimal
olduğu iddia edilmeyen sabit 500-MFW reference ile çalışır. Research Mode görünür
ama kilitlidir. Exact implementation commit'i
`7e9a28eafa4756b2cf82e6d6f3d8e0c43742edf5`; canonical Linux CI
`29388984019` içinde 1.459 test, gerçek upload-to-R/stylo Playwright akışı,
desktop/mobile/reflow, payload canary, console/network, SBOM/dependency/secret ve
Linux amd64 container kapıları geçti. Aynı commit remote no-hardlinks clean clone'da
bootstrap/full verify ve temiz post-run tree ile tekrarlandı. Kanıt:
`RUN-20260715-0002` ve
`provenance/evidence/P008/minimum-alpha-workflow-validation.md`. İki önceki CI
failure, gerçek calculation başarısızlığı değil harness sınırı düzeltmeleri olarak
değiştirilmeden tutulur. P008-AC-09 tam üç amaç ve ilgili known/unknown scope'lar
için pending kalır.

**P007 diagnostics checkpoint'i:** Purpose-aware metadata confound engine ve tek
immutable health projection implementation commit'i
`b42da99442f4c2a7f617da082c699f1f48942b62` ile tamamlandı. Length,
transformation, confound, overlap ve MFW capacity panelleri aynı projection'dan
semantic table ve CSV üretir; stale binding fail-closed olur. Full yerel ve remote
clean-clone kapısı 1.402 test, bir documented macOS skip, 10.088 statement, 2.642
branch ve yüzde 100 coverage ile geçti. GitHub Actions `29381188842` bütün 1.403
Linux testini, SBOM/dependency/secret gate'lerini ve canonical Linux amd64 image'i
geçti. 1440px desktop ve 390px mobile browser denetiminde overflow/clipped copy/
console error yoktu; üç research-purpose guidance'ı doğru değişti. Kanıt:
`provenance/evidence/P007/corpus-health-diagnostics-validation.md` ve
`RUN-20260715-0001`. Native browser file chooser ile son owner warning-copy turu
bilinçli olarak açıktır; genel usability iddiası kurulmaz.

**P007 web integration checkpoint'i:** Browser intake bytes her geçişte yeniden
P003 doğrulamasından geçirilip P005 private prepare-only workspace'e taşınıyor.
Streamlit state yalnız opaque owner key ile payload-free receipt/outcome tutuyor;
capability, secret, raw/prepared text ve server path taşımıyor. Final metadata
confirmation sonrasında fixed `delta-surface-words-v1` açıklaması, work role/OCR/
paratext annotations, deterministic preparation, READY/BLOCKED health summary,
token-length visualı, MFW capacity ve content-free downloads bağlıdır. Üretim
runtime'ı explicit private root ile birbirinden farklı iki 256-bit secret olmadan
fail-closed; process start ve yeni kabul öncesi durable P005 state uzlaştırılır,
expired idle lease'ler toplanır ve terk edilmiş oturumların staged kapasiteyi
kalıcı tüketmesi engellenir. Final local `./scripts/verify.sh`: 1.379 passed, bir
documented Linux-only macOS skip, 9.758 statement, 2.570 branch ve yüzde 100
coverage. Gerçek browser kontrolünde desktop ve 390 px mobile yatay taşma vermedi,
araştırma yolu seçimi çalıştı ve console error/warning kaydı boştu. Exact-commit CI
run `29378757244` içinde verify job `87237608831` ile 1.380 Linux testi ve container
job `87237608822` ile canonical Linux amd64 image build geçti. Exact implementation
commit'i `9b5790f3c75170f9c4241fad11d51f2a26495857`; kanıt:
`provenance/evidence/P007/web-preparation-validation.md`.

**Yeni insan kararları:** `HD-20260714-0001` P007 yöntem paketini kabul etti ve
ADR-0014 Accepted oldu. `HD-20260714-0002` ile ADR-0015, bütün minimum kapılar
geçerse 2026-07-17 için açıkça etiketli Public-alpha hedefini ve tamamlanan kanıta
dayalı Ağustos 2026 tam makale taslağını kabul etti. Hız hedefi başarısız bir
privacy, admission, calculation, explanation, resource, isolation, rollback veya
Lemmata smoke kapısını geçersiz kılmaz.

**P007 açılış checkpoint'i:** P006 main merge commit'i `5fab67c`; main CI
`29354208853` yeşil. `codex/p007-preprocessing` dalında pre-edit gate 1.246 passed,
bir documented macOS skip, 7.768 statement, 2.080 branch ve yüzde 100 coverage ile
geçti. Dört adet 30k-token read-only mercek yöntem, architecture/security,
FAIR/provenance ve beginner UX'i denetledi. Ana bulgular: payload-free P004 state
P007'ye ham metin veremez; P003 bytes P005 private prepare-only workspace'e doğrudan
bağlanmalıdır; lower-level P005/P006 yolları corpus health'i bypass etmemelidir;
P006 input yalnız blocker-free, hash-bound, one-time READY receipt ile kurulmalıdır.
Accepted profil `delta-surface-words-v1`; exact/near/shared-passage, 6-work,
3-chronology-point, 4:1 length ve 3:1 group eşikleri Delta v0.1 policy'dir, evrensel
stilometri yasası değildir.

**P006 closure checkpoint:** Fixed worker ve scientific handoff `f0800c8` ile
uygulandı. Capture source `79cb268`, read-only capture `29340236382`, evidence-only
commit `7359cbe` ve `RUN-20260714-0004` exact worker package'ını bağlar. Geçici
capture job kaldırıldı. Durable audit commit `d676d90`, normal Linux CI
`29350106890` içinde verify job `87143854938`, container job `87143854913`, tüm
1.247 test, worker parity, scientific handoff, yüzde 100 measured coverage ve
SBOM/dependency/secret kapılarından geçti. Aynı commit GitHub origin'den fresh
remote no-hardlinks clone'a alındı; bootstrap/full verify geçti ve post-run tree
temiz kaldı (`RUN-20260714-0005`). P006-AC-01 ile P006-AC-08 fixture-local sınırda
passed. Preprocessing parity, benchmark accuracy, public workflow, FAIR export,
Pinokyo ve production iddiaları çıkarılamaz.

**P006 başlangıç bulgusu:** Process exit zero bilimsel başarı değildir. Guardian ACK
öncesi output schema ve scientific invariant doğrulaması gerekir. stylo 0.7.71
`perform.delta` Wurzburg yolu combined known/unknown table'ı yeniden scale edebilir;
P006 Cosine Delta known-derived z-scores üzerinde `dist.cosine` kullanacaktır.
CC0 fixture, C.UTF-8/UTC, seed 20260713, 1e-6 parity ve 1e-12 structural/tie
protokolü `HD-20260713-0002` ile kabul edildi. Bu karar parity sonucu veya P006
kabulü değildir.

**P006 sözleşme checkpoint'i:** Üç bağımsız denetim iki bilimsel ve beş güvenlik/
mimari blocker buldu. Aggregate count ayrı 150 milyon sınırına alındı; büyük JSON
integer fail-closed oldu; zero-overlap projection, culling equality, unknown-only
feature, token-total denominator ve UTF-8 tie testleri eklendi; FIFO pre-open
reddi, nonblocking read, tek JSON parse ve current-area rebinding uygulandı. Erken
validated-ACK kodu crash-safe olmadığı için tamamen çıkarıldı ve AC-03 bu ara
checkpointte pending kaldı. Ara local `./scripts/verify.sh`: 1.073 test, 7.215 statement, 1.898 branch,
yüzde 100 kapsam kapısında geçti. Son bilimsel yeniden denetim, erişilebilir Classic
Delta değerlerini kesen keyfi `1e12` sınırını buldu; sınır finite IEEE-754 double
alanına çıkarıldı ve `>1e12` regresyonu eklendi. Normal dosyadan FIFO'ya pre-open
yarış testi de eklendikten sonra final local `./scripts/verify.sh`: 1.075 test,
7.216 statement, 1.898 branch, yüzde 100 coverage; metadata, 80 provenance record,
repository scan ve R lock geçti. Bilimsel denetçinin son dar yeniden incelemesi PASS
verdi.
Exact implementation commit `3c6ebe539b6c0a7f28c295cdcd74bc7e58135f6f`,
GitHub Actions run `29291282495` içinde verify job `86955214522`, SBOM/dependency
audit ve canonical Linux amd64 container job `86955214531` kapılarından geçti.
Bu ara checkpointte P006-AC-01 ve P006-AC-05 passed; AC-03 ve worker/parity
ölçütleri sonraki P006 adımlarına pending kaldı.

**P006 oracle checkpoint'i:** Source `7df1fdf` normal CI `29295419945` ve
one-time capture `29295419981` kapılarından geçti. Locked Linux amd64 oracle iki kez
ağsız çalıştı; complete base, unknown-canary, partial-boundary ve session dosyaları
byte-identical çıktı. Bot commit `b5a842f`, `RUN-20260714-0001` ve
`provenance/evidence/P006/oracle-freeze-validation.md` source/image/package/input/
output hashlerini tutar. Üç önceki capture; broad error sınıfı, unreadable `renv`
cache ve public synthetic output izni açıklarını bulup kanıt yazmadan durdu. Geçici
write workflow kaldırıldı ve frozen-package validator normal verify'a eklendi. Bu
checkpoint worker parity veya P006 acceptance değildir; passed ölçütler değişmedi.
Post-freeze method audit, v1'de bütün `token_total` değerlerinin 100 ve tek unknown
satırının son konumda olduğunu buldu. Bu nedenle v1 doğru çalışmış fakat kabul için
yetersiz ara referanstır; v2 üretilmeden worker karşılaştırmasına geçilmez.

**P006 v2 freeze durumu:** `p006-whole-text-v2` fixture; unequal totals, iki
interleaved unknown, known final row, iki-unknown canary ve order permutation içerir.
Formula-level raw-count counterfactualı her dört fit ve üç distance family için
normalized sonuçtan aktiftir. `scripts/validate_p006_fixture_v2.py`, suite-aware
oracle validator/freeze aracı ve CI içinde manual-only read-permission capture job'u
eklendi. Capture job repo commit/push yapamaz; yayınlama yerel ve ayrı olacaktır.
Yerel `scripts/verify.sh` 1,094 test, 7,247 statement, 1,902 branch ve yüzde 100
kapsamla geçti. V2 source `c1ea852` ve normal CI `29298402134`; read-only capture
registration `94fac26` ve normal CI `29298843070` ile yeşildir. Dispatch
`29298977429` iki oracle koşusu ile validation/package adımını geçti, fakat GitHub
artifact-storage kotası upload'u reddetti. `p006_log_transport.py` aynı küçük paketi
canonical, chunked ve SHA-256-bound olarak job logundan taşımak için eklendi; tam
transport source `c6a07e1`, normal CI `29299641848` ve successful capture
`29299793944` ile geçti. Envelope `c94f84b3...4216c`, evidence-only commit `42fe09b`
ve publication CI `29300077689` ile donduruldu. `RUN-20260714-0002` zinciri bağlar;
kalıcı v2 validator normal verify'a eklendi ve geçici capture job kaldırıldı. V2
audit commit `ad8aa77` ve normal CI `29300681277` de yeşildir. V2 fixed worker
karşılaştırması için hazırdır; passed AC listesi değişmemiştir.

**P005 closure checkpoint:** `HD-20260713-0001` ile kabul edilen Git-backed kanal,
exact Ubuntu capture run `29268150070`, normal source CI `29268150409`, evidence
commit `2eff470` ve `RUN-20260713-0004` ile geçti. Geçici write workflow'u kaldıran
`029248b`, normal closure CI run `29269051028` içinde verify job `86881820484` ve
container job `86881820512` ile yeşildir. P005-AC-01--AC-08 passed; blocker yoktur.
Bu kapanış gerçek R/stylo, production retention/isolation, secure erase, deployment
ve final owner walkthrough iddiası değildir.

**P005 acceptance checkpoint:** İlk bağımsız closure denetimi capability-first
authorization, zero-allocation admission, cleanup-failure accounting, cancellation
delivery, reciprocal guardian ACK ve descriptor-bound process start açıkları buldu;
tamamı kapatıldı. Final exact replay `RUN-20260713-0003`, commit `2a17ec6` üzerinde
950 test, 6.551 statement, 1.732 branch, yüzde 100 coverage, clean clone ve iki
browser harness ile geçti. Linux CI önce emergency reap'te unreaped leader buldu,
sonra platform-dependent coverage branch'i buldu; ikisi de düzeltildi. Final run
`29220278021` Linux verify, evidence generation ve canonical container'ı geçirdi.
Upload GitHub quota recalculation nedeniyle reddedildi; hard gate korunuyor. Kanıt:
`provenance/evidence/P005/acceptance-hardening-validation.md`,
`provenance/evidence/P005/final-ci-validation.md` ve
`memory/checkpoints/2026-07-13-p005-acceptance.md`.

**P005 guardian checkpoint:** Ayrı POSIX-session guardian, app-liveness pipe,
`waitid(..., WNOWAIT)` leader ownership, durable SQLite terminal ACK ve
job+execution-bound HMAC recovery receipt uygulandı. Running-worker ve
post-completion app-loss yarışları gerçek `SIGKILL` ile geçti; thread-start,
malformed control, double-control-failure ve persistent reap yolları kapatıldı. Dört
bağımsız adversarial turdaki bütün P0/P1 bulguları kapandı. Full gate 878 test,
6.060 statement, 1.602 branch ve yüzde 100 coverage ile geçti. Kanıt:
`provenance/evidence/P005/guardian-app-loss-validation.md`.
Exact implementation commit aynı kilitlerden fresh no-hardlinks clone'da yeniden
kuruldu; 878-test gate geçti ve clone temiz kaldı (`RUN-20260713-0001`).
Provenance-link commit `cfb503c`, GitHub CI run `29215163561` içinde verify job
`86709522502` ve container job `86709522510` ile tamamen yeşildir. Kanıt:
`provenance/evidence/P005/guardian-exact-commit-ci.md`.

**P005 retention checkpoint:** `0e84b10` ile SQLite deletion ledger, schema-v1
migration, fail-closed optional workspace load, exact staged/queue/result/export
deadlines, continuous janitor, success-before-publication cleanup ve verified-absence
tombstone purge uygulandı. Full gate 795 test, 5.262 statement, 1.404 branch ve yüzde
100 coverage ile geçti. Kanıt:
`provenance/evidence/P005/retention-janitor-validation.md`.

**P005 tarihsel P0 bulgu, kapatıldı:** Bağımsız süreç denetimi eski daemon monitorün
app process ile öldüğünü ve worker grubunu bırakabildiğini doğrulamıştı. Kalıcı
PID/PGID çözümü identifier reuse nedeniyle reddedildi; `3c746d1` guardian katmanı bu
yerel macOS açığını kapattı. Final Linux verify ve container artık geçti; yalnız
retained supply-chain artifact ve P005-AC-08 kapanışı açıktır.

**P005 foundation checkpoint:** Commit'ler `bce5bb2`, `0da9a1b`, `5e1cbba` ve
`eca5357`; full gate 769 test, 4.947 statement, 1.304 branch ve yüzde 100 coverage
ile geçti. SQLite concurrency/ownership, macOS-safe `setrlimit + execve` launcher,
nested process cancellation, workspace load/selective cleanup ve fail-closed canary
testleri dahildir. Kanıt:
`provenance/evidence/P005/foundation-validation.md`. Bu ara checkpoint P005 kapanışı,
Linux CI, production isolation, gerçek R/stylo veya CE-14/CE-15 doğrulaması değildir.

**P005 başlangıç baseline'ı:** P004 merge commit `d13e63c`, main CI run
`29208223198` içinde verify, SBOM/dependency audit ve Linux amd64 container
işlerinde geçti. Dört read-only ajan security, lifecycle/retention, accessible UX
ve FAIR/claim mercekleriyle P005'i denetledi. Kanonik baseline:
`decisions/ADR-0012-job-lifecycle-retention.md` ve
`provenance/evidence/P005/architecture-audit.md`.

**P005 kritik sınır:** Job ID ownership değildir; ayrı session capability ve
payload-free SQLite control store kullanılır. Execution outcome cleanup state'inden
ayrıdır. Public P004 flow P006/P008'e kadar payload-free ve analysis-locked kalır.
P005 yalnız application-managed local deletion ve intra-Delta session isolation
kanıtı üretebilir; CE-14 production dili ve CE-15 P014/P015'e aittir.

**İnsan kabul sırası değişikliği:** Oğuz `HD-20260712-0002` ile ara testleri
Codex'in yürütmesini, ortak walkthrough'un ürün hazır olduğunda yapılmasını istedi.
Bu karar P004'ü tek başına kabul etmedi; ardından expanded browser, full repository,
exact-commit ve CI kapıları geçerek teknik kapanış yapıldı. Safari, VoiceOver,
bilimsel sonuç ve final release kabulü bu otomatik kanıttan türetilmez.

**P004 otomatik kabul provası:** Tracked browser harness'a permission-required
blocker, exact rights correction, guided-value restoration, analysis-only action
matrix ve post-correction confirmation turu eklendi. On bir başarısız harness/oracle
iterasyonu raporlandı; on ikinci final koşum altı viewport, Guided TXT, rights
correction, Review/download ve two-member ZIP akışlarında, sıfır external host,
sıfır console error, sıfır payload echo ve sıfır overflow ile geçti. Working-tree
full gate 468 test, 3.174 statement, 880 branch ve yüzde 100 coverage ile yeşildir.
Kanıt: `provenance/evidence/P004/automated-acceptance-rehearsal-validation.md`.
Implementation commit `9f3124a`, fresh `--no-hardlinks` detached clone'da
committed lockfile'lardan yeniden kuruldu; aynı 468-test full gate ve expanded
browser audit tamamen geçti, clone temiz kaldı. `RUN-20260712-0005` ile exact
report/checksum paketi bu sonucu kaydeder. Provenance-link commit `c8ae4c2`, GitHub
CI run `29207801898` içinde verify, SBOM/dependency audit ve Linux amd64 container
işlerinde geçti. `HD-20260712-0002` uyarınca P004 repeatable teknik kapıları
tamamlandı; final owner walkthrough P015'te açık kalır.

**Kabul edilen P004 UX:** Form + versioned CSV, progressive disclosure, bir TXT =
bir bağımsız eser, exact-confirmed mapping, uncertainty-aware chronology, ayrı rights
actions, üç seviyeli validation ve görsel Corpus Review. Ayrıntı:
`docs/development/p004-metadata-ux-decisions.md`.

**Tasarım kapısı:** Üç adet 10 soruluk karar turu tamamlandı. Corpus iç akışı
Upload, Describe, Review; metadata zorunlulukları purpose-aware; kaynak URL veya
bibliyografik künye; rights eylem bazlı fail-closed; yardım katmanlıdır. Karar
`HD-20260711-0010`, uygulama sırası aynı UX sözleşmesinin 7. bölümündedir.

**CI durumu:** GitHub shallow-checkout kaynaklı provenance hatası `f7a75b0` ile
düzeltildi ve `0b0b349` ile main'e alındı. Hotfix run `29167750356` ve main run
`29167865311` verify, SBOM/audit ve container işlerinde tamamen yeşildir.

**P004 CSV doğrulaması:** Ayrı rights-source kaybı, statement-only public export,
external schema drift ve yanlış field mapping bağımsız denetimde bulunup düzeltildi.
`8dd85c1` temiz yerel ağaçta 390 test ve %100 statement/branch coverage ile geçti;
`RUN-20260711-0006` bunu kaydeder. GitHub CI `29172847800` verify, SBOM/audit ve
Linux container işlerinde geçti; ayrıntı
`provenance/evidence/P004/metadata-csv-validation.md`.

**P004 Guided UI doğrulaması:** Individual TXT Upload -> Describe -> Review akışı,
payload-free catalog, deterministic rights questionnaire, timeline, Rights Action
Matrix, readiness counters ve üç documentation download uygulanmıştır. Fresh-process
Playwright altı viewport'ta geçti; `./scripts/verify.sh` 418 test ve yüzde 100
statement/branch coverage ile yeşildir. Kanıt:
`provenance/evidence/P004/guided-corpus-workflow-validation.md`.

**P004 Review projection doğrulaması:** Beş composition boyutu ve yedi sütunlu
Metadata Completeness Matrix tek immutable projection'dan üretilir; görsel, semantic
table ve iki P003-validated CSV aynı anahtarları taşır. İlk focus failure ve otomatik
geçmesine rağmen manuel olarak reddedilen clipped-count görüntüsü korunmuştur.
Passing fresh-process Playwright altı Review viewport'unda key parity, work x 7
matrix, keyboard focus, no overflow, no external host ve no payload echo kapılarını
geçti. Full aday 457 test ve yüzde 100 statement/branch coverage ile geçti. Kanıt:
`provenance/evidence/P004/review-projection-validation.md`.

**P004 Timeline/correction/confirmation doğrulaması:** Timeline artık canonical
projection üzerinde seçilebilir; matrix field path'leri exact guided work/section'a
veya source CSV `work_id` + field düzeltmesine yönlenir; guided metadata Review
dönüşünde payload-free state ile korunur. Mapping/rights acknowledgement inventory
SHA-256'ya bağlıdır, blocker varsa disabled ve rebuild ile invalidated olur. Mobil
custom header örtüşmesi manuel görüntü denetiminde bulunup düzeltildi. Final aday
464 test, 3.132 statement, 868 branch ve yüzde 100 coverage ile; fresh-process
Playwright altı viewport, keyboard confirmation, no overflow, no egress ve no
payload echo ile geçti. Kanıt:
`provenance/evidence/P004/timeline-correction-confirmation-validation.md`. P004 kabul
edilmedi; GitHub CI ve human acceptance açıktır.

**P004 Guided ZIP doğrulaması:** P003'ün zaten güvenli intake sırasında hesapladığı
member label, SHA-256, byte, line, token ve limit profile değerleri immutable,
payload-free receipt olarak P004'e açıldı. ZIP yeniden parse veya extract edilmiyor;
individual TXT ve ZIP member aynı deterministic catalog'a giriyor. Upload member
catalog'u görünür, iki member iki guided form ve iki Review work satırı üretiyor;
payload ve storage adları Describe state'ine taşınmıyor. Individual-TXT regression
ile iki-member ZIP fresh-process Playwright'ta geçti. Full aday 467 test, 3.165
statement, 878 branch ve yüzde 100 coverage ile yeşildir. Dört başarısız
harness/oracle koşusu korunmuştur. Kanıt:
`provenance/evidence/P004/guided-zip-member-catalog-validation.md`. P004 kabul
edilmedi; GitHub CI ve human acceptance açıktır.

**P004 exact-commit doğrulaması:** Birleşik Guided UI implementation commit'i
`c82740d` yeni bir `--no-hardlinks` klona alındı ve detached HEAD üzerinde committed
Python/R lockfile'larından bootstrap edildi. `./scripts/verify.sh` 467 test, 3.165
statement, 878 branch ve yüzde 100 coverage ile geçti; aynı klonda fresh-process
individual-TXT + two-member ZIP browser audit de tamamen geçti. Klon koşumlardan
sonra temiz kaldı. `RUN-20260712-0001` ve
`provenance/evidence/P004/guided-ui-exact-commit/report.md` bu kapıyı kaydeder.
Provenance-link commit'i `4c3bb8a` GitHub CI run `29190917436` üzerinde verify,
SBOM/audit ve canonical Linux amd64 container işlerinde geçti. Kanıt:
`provenance/evidence/P004/guided-ui-ci.md`. Bu checkpointte insan kabulü açıktı;
sonraki `HD-20260712-0002` teknik kapanış sırasını P015 final walkthrough'undan ayırdı.

**P004 beginner-first entry revizyonu:** İlk Purpose/Upload yüzeyi artık stilometriyi
ölçülebilir dil kullanım örüntülerinin corpus-relative karşılaştırılması olarak
tanımlar; Observe -> Compare -> Interpret haritasını analiz sonucu olmadığını
belirterek gösterir; Compare Texts, Compare Groups ve Trace Style Over Time için
Question, Why use it ve Do not conclude açıklamalarını görünür tutar. Sahte sonuç
grafiği, AI, analiz veya yeni storage katmanı eklenmedi. Mobile yöntem adımları
satırlara dönüştürüldü, dekoratif token alanı gizlendi ve 320px first-action görünür
hale geldi. Final fresh-process audit altı viewport ile individual-TXT ve two-member
ZIP regression'ı geçti; başarısız denemeler saklandı. Kanıt:
`provenance/evidence/P004/entry-experience-redesign-validation.md`. Repository-wide
gate 467 test, 3.167 statement, 880 branch ve yüzde 100 coverage ile geçti.
Implementation commit `b538807`, `RUN-20260712-0002` ile fresh no-hardlinks
detached clone'da aynı full gate ve browser audit'ten geçti; clone temiz kaldı. CI
run `29192912269`, provenance-link commit `26a04e3` için verify, SBOM/dependency
audit ve Linux amd64 container işlerinde geçti. Bu checkpointte revize insan kabulü
açıktı; sonraki otomatik teknik kapanış kaydı bu tarihsel durumu supersede etti.

**P004 Lemmata aile paleti ve parametre yönlendirmesi:** Canlı `lemmata.app` ve
`lda.lemmata.app` denetiminden koyu yeşil eylem, açık gri canvas/sidebar ve soft
mint öğretici yüzeyler Delta'ya taşındı. Koyu `Current boundary` sidebar'ı Start
here, üç adım, neden-parametreler-sonra açıklaması ve collapsed Technical status'a
dönüştü. Ana akış Guided 100/300/500/1000 MFW, sabit 500 MFW + yüzde 0 culling +
whole text + Classic Delta referansı ve bounded Research Mode'un en fazla 24
belgeli kombinasyonunu açıklar; gerçek kontroller P006/P007/P008 tamamlanmadan
kilitli kalır. İlk browser koşusu parameter-placement ve mobil sidebar oracle'ında
fail olarak saklandı; ikinci koşu altı viewport, computed palette, kontrast, TXT/ZIP,
no-overflow, no-egress ve clean console kapılarında geçti. İlk full gate formatting
üzerinde durdu; format sonrasında 468 test, 3.171 statement, 880 branch ve yüzde
100 coverage ile geçti. Kanıt:
`provenance/evidence/P004/family-palette-parameter-orientation-validation.md`.
Exact implementation commit `54e479d`, `RUN-20260712-0003` ile fresh
no-hardlinks detached clone'da bootstrap, 468 test, yüzde 100 coverage ve aynı
browser audit'inden geçti; clone temiz kaldı. Provenance-link commit `5d95ce4`,
GitHub CI run `29201459098` içinde verify, SBOM/dependency audit ve Linux amd64
container işlerinde geçti. Bu checkpointte insan kabulü açıktı; P004 daha sonra
`HD-20260712-0002` sınırlarıyla teknik olarak kapatıldı.

## Tarihsel P004 Okuma Listesi

Aşağıdaki liste P004 aktifken kullanılan tarihsel devirdir; güncel P007 başlangıç
talimatı değildir. Güncel sıra bu dosyanın üst bölümü ve START_HERE.md içindedir.

1. `START_HERE.md`
2. Bu dosya
3. Roadmap'teki P004 bölümü
4. Claim CE-09 ve CE-13
5. Threat RP-01, RP-02, EPI-01 ve EPI-07
6. `provenance/tickets/P003.json` kapanış sınırı
7. `docs/methodology/pinocchio-diachronic-worked-example.md` içindeki metadata ve rights alanları
8. `provenance/tickets/P004.json` ve `prompts/P004-start.md`

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
- **Tarihsel sonraki adım:** P003 insan kabul kapısıydı; bu kapı artık `HD-20260711-0008` ile tamamlandı.

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

- P003 application intake uygulanmıştır; lifecycle ve retention P005'te bağlıdır.
  Canlı proxy/host buffering gözlemi ve son P014 host kabulü açıktır.
- Asset metadata, corpus inventory, rights kararları ve correction akışı P004'te
  uygulanmıştır; farklı gerçek corpuslarda genel yeterlilik iddia edilmez.
- Gerçek R/`stylo` execution P006'da ve sentetik upload-to-export browser E2E
  P008/P009'da kanonik Linux üzerinde geçmiştir; benchmark accuracy, calibration
  ve edebî bulgu doğrulanmamıştır.
- Screen-reader ve tam WCAG conformance değerlendirmesi yapılmadı.
- Proxy/TLS/Host/CORS/CSRF/header paketi P014 CI'da test edilmiştir; canlı
  shared-VPS readiness, coexistence, rollback ve tam isolation iddiası yoktur.
- General usability veya ease claim'i yoktur.
- `lemmata.app` üzerinde `Launch Stylometry` bağlantısı eklenmedi; ayrı sonraki ticket'tır.

Bu maddeler gizlenmiş pass değildir. Claim ve threat kayıtlarında açık kalan kapı
olarak tutulur.

## P003 Uygulama Sonucu

- Explicit TXT veya ZIP corpus rolü ve ayrı metadata CSV uploader'ı var.
- MIME verilirse rolle uyuşmak zorunda; içerik parser'ı her durumda zorunlu.
- UTF-8/NFC, belge imzası, metin/CSV limitleri ve injection kontrolleri var.
- Katı ZIP v1; ham EOCD/central/local tutarlılığı, no ZIP64/extra/comment,
  canonical path, link/device/nested archive reddi ve ikinci-okuma hash kontrolü var.
- Rejected uploader payload ve filename yeni widget anahtarıyla temizleniyor; yalnız
  bir content-free kod bir rerun boyunca gösteriliyor.
- 232 test ve yüzde 100 statement/branch coverage geçti; taze-süreç browser
  harness altı viewport ve sentetik TXT/CSV/ZIP/rejection akışlarında geçti.
- Başarısız browser paketleri ve additive path errata korunuyor.
- Exact implementation commit `60bb93e4554cf7fa2827014b719cc8eb427a9ada`,
  canonical `bootstrap.sh` ile yeni klonda kuruldu; `RUN-20260711-0003` geçti ve
  `provenance/evidence/P003.sha256` bütün P003 kanıtını mühürledi.
- Bağımsız UI, güvenlik ve FAIR yeniden denetimlerinde açık P0/P1/P2 kalmadı.

P003'te metadata anlamı/rights, gerçek analysis, Pinokyo data, retention süreleri,
production deployment, parent-site launch, PDF/DOCX/EPUB/TEI veya OCR eklenmedi.
Oğuz manuel TXT+CSV, ZIP ve unsafe-CSV rejection turunu tamamladı ve
nihai `HD-20260711-0008` ile kabul verdi. İnsan kanıtı otomatik paketi değiştirmeden
`RUN-20260711-0004` ve ayrı checksum manifestiyle tutulur.
İnsan kabul kayıtlarını içeren `d99aa7158caa8ba78ac8b2c1810eb61d9d21b8a2`
exact commit'i temiz çalışma ağacında `RUN-20260711-0005` ile yeniden doğrulandı;
232 test, yüzde 100 statement/branch coverage ve bütün repository kapıları geçti.

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

- Kanonik yerel çalışma kopyası `~/Developer/delta.lemmata_app` yolundadır.
- `origin`, özel `https://github.com/oguzkoran-max/delta.lemmata.app`
  repository'sidir; bu henüz public release değildir.
- Varsayılan uzak dal `main`; P001-P009 minimum akışları ve PR #7'ye kadar P014
  altyapısı main'e alınmıştır. Aktif geliştirme dalı
  `codex/p014-visual-phase-b`; draft PR #8'in exact implementation commit'i
  `3a554e0e76522672efaf547b1d03e12cb4f3531b`'dir.
- Google Drive artık Delta repository'si veya geliştirme ortamı için kaynak
  değildir. `.venv`, `.tools` ve cache dosyaları yeniden üretilir, eşitlenmez.
- Parent akademik-asistan repository'si Delta dosyalarını izlemez; yalnız proje
  wiki'si yeni kanonik yola işaret eder.
- Repository taşıması P003 acceptance kanıtı değildir; P003'ün ayrı insan kabulü
  `HD-20260711-0008` ve `RUN-20260711-0004` ile tamamlanmıştır.

## Tarihsel P004 Tasarım Checkpoint (2026-07-12)

- Exact sibling palette ve Language Weave implementation localde tamamlandı.
- Passing browser evidence:
  `provenance/evidence/P004/exact-family-language-weave-attempt-6/`.
- Validation report:
  `provenance/evidence/P004/exact-family-language-weave-validation.md`.
- Full local gate: 468 test, 3.174 statement, 880 branch, yüzde 100 coverage.
- Exact commit `374e2d0`, `RUN-20260712-0004` ile fresh no-hardlinks clone'da
  bootstrap, full gate ve browser audit'ten geçti; clone temiz kaldı.
- Provenance-link commit `9864db4`, GitHub CI run `29204391922` içinde Linux
  verify, SBOM/dependency audit ve canonical amd64 container işlerinde geçti.
- Attempts 1-5 machine-readable failure olarak korunuyor; yalnız final attempt
  full screenshot setini taşıyor.
- Scientific analysis, parameter controls, Safari, VoiceOver ve P004 human
  acceptance hâlâ açık. Sonraki iş: Oğuz'un revised walkthrough'u.
