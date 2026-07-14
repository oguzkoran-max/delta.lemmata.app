# Delta Session Handoff

**Güncellendi:** 2026-07-14

**Aşama:** P001-P006 tamamlandı. P007 Deterministic Preprocessing and Corpus
Health aktif; implementation, önerilen yöntem paketinin ayrı insan kararını bekliyor

**Kod durumu:** P004 guided corpus akışına ek olarak P005'te versioned lifecycle,
256-bit session/job identity, payload-free atomic SQLite queue, private workspace,
validated-payload staging, capability-first application service, synthetic POSIX
process controller, kalıcı content-free deletion ledger, continuous fake-clock
janitor, ayrı app-loss guardian, durable SQLite terminal ACK ve execution-bound
recovery receipt var. P006 kapalı input/result/fatal-error şemaları, strict tek-parse
parser, input-dependent semantic validator, process sonucundan ayrı saf scientific
finalizer, bounded no-follow workspace read, fixed R worker, shell-free adapter,
checksum-frozen direct-`stylo` oracle, retained worker package ve crash-safe
scientific-result handoff var. Public analysis, preprocessing, corpus health,
benchmark, stability, FAIR run export ve deployment hâlâ yok

**Son tamamlanan ticket:** `provenance/tickets/P006.json` (`complete`)

**Aktif ticket:** `provenance/tickets/P007.json` (`in-progress`)

**Sıradaki tek ana iş:**
`docs/development/p007-preprocessing-corpus-health-contract.md` içindeki on maddelik
öneriyi Oğuz'a sade Türkçeyle sun. Kabul veya revizyonu ayrı HumanDecision olarak
kaydet; sonra schema-first ve tests-first uygulamaya geç. ADR-0014 Proposed iken
implementation, fixture freeze veya threshold claim'i üretme. Public workflow P008,
benchmark P010/P011, FAIR package P012, Pinokyo P013 ve production isolation P014'te
kalır.

**P007 açılış checkpoint'i:** P006 main merge commit'i `5fab67c`; main CI
`29354208853` yeşil. `codex/p007-preprocessing` dalında pre-edit gate 1.246 passed,
bir documented macOS skip, 7.768 statement, 2.080 branch ve yüzde 100 coverage ile
geçti. Dört adet 30k-token read-only mercek yöntem, architecture/security,
FAIR/provenance ve beginner UX'i denetledi. Ana bulgular: payload-free P004 state
P007'ye ham metin veremez; P003 bytes P005 private prepare-only workspace'e doğrudan
bağlanmalıdır; lower-level P005/P006 yolları corpus health'i bypass etmemelidir;
P006 input yalnız blocker-free, hash-bound, one-time READY receipt ile kurulmalıdır.
Proposed profil `delta-surface-words-v1`; exact/near/shared-passage, 6-work,
3-chronology-point, 4:1 length ve 3:1 group eşikleri henüz insan kabulü değildir.

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

- P003 application intake uygulanmıştır; production retention ve proxy/host buffering P005/P014'te açıktır.
- Asset metadata, corpus inventory ve rights kararları P004'tür.
- Gerçek `stylo` execution/parity P006'dır.
- Upload-to-export no-code E2E henüz kurulmadı.
- Screen-reader ve tam WCAG conformance değerlendirmesi yapılmadı.
- Proxy/TLS/Host/CORS/CSRF/header ve shared-VPS isolation P014'tür.
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
- Varsayılan uzak dal `main`; P003 `d5a8118` merge commit'iyle alınmıştır.
  Aktif geliştirme dalı `codex/p004-metadata-rights` dalıdır.
- Google Drive artık Delta repository'si veya geliştirme ortamı için kaynak
  değildir. `.venv`, `.tools` ve cache dosyaları yeniden üretilir, eşitlenmez.
- Parent akademik-asistan repository'si Delta dosyalarını izlemez; yalnız proje
  wiki'si yeni kanonik yola işaret eder.
- Repository taşıması P003 acceptance kanıtı değildir; P003'ün ayrı insan kabulü
  `HD-20260711-0008` ve `RUN-20260711-0004` ile tamamlanmıştır.

## Aktif P004 Tasarım Checkpoint (2026-07-12)

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
