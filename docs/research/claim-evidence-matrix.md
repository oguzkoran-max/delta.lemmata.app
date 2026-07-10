# Delta Claim-Evidence Matrix

**Durum:** P001 sonrası kanonik claim planı
**Tarih:** 2026-07-10  
**Kanıt durumu:** P001 temel ve provenance kontrolleri var; ürün ve bilimsel sonuç claim'leri henüz doğrulanmadı

## 1. Kullanım Kuralı

Bu dosya site, dokümantasyon ve makalede kurulabilecek her önemli iddiayı kanıta bağlar. Bir claim yalnız kendi gate'i geçtikten sonra kesin ifadeyle kullanılabilir. Gate başarısızsa fallback language kullanılır.

Başarı, olumlu bir edebî sonuç bulmak değildir. Delta'nın kırılgan, confounded, hakları belirsiz veya yeniden üretilemeyen bir sonucu açıkça göstermesi de başarılı davranıştır.

Durum değerleri:

- `planned`: Kanıt tasarlandı, uygulama yok
- `implemented`: Kontrol var, bağımsız doğrulama yok
- `verified`: Acceptance gate geçti
- `failed`: Gate geçmedi; yalnız fallback language kullanılabilir
- `not-applicable`: İddia sürüm kapsamından çıkarıldı

## 2. Ürün ve Yöntem Claim'leri

| ID | Kesin claim, yalnız verified ise | Kanıt ve acceptance gate | Artifact | Ticket | Gate başarısızsa fallback language |
|---|---|---|---|---|---|
| CE-01 | `Delta exposes its supported v0.1 workflows through a browser; starting and completing them requires neither prior R/Python coding nor user-authored R/Python code.` | Text Proximity, Group Comparison ve Style Over Time akışları upload'dan export'a browser E2E ile tamamlanır; code/config input yok; sıfır shell veya kullanıcı kodu; documented prerequisites içinde R/Python yok; sıfır açık critical defect | `no-code-e2e-report.json`, prerequisite audit, expert checklist | P002, P008, P009, P015 | `Delta was designed to remove R/Python coding from its supported workflows; ease of use and learnability were not established.` |
| CE-02 | `Delta makes corpus checks, parameter choices and sensitivity, interpretive limits, and run provenance mandatory outputs.` | Her başarılı run'da `corpus_health`, `parameters`, `limitations` ve provenance bulunur; uyarılar sonuçtan ayrı gizlenemez; yasak dil testi sıfır ihlal | `method-visibility-traceability.json`, UI snapshots, export fixtures | P004, P007, P009, P011, P012 | `Delta was designed to expose methodological decisions; its effect on research practice was not empirically measured.` |
| CE-03 | `Delta performs work-level stylometry across independent works; it does not align versions, compute textual diffs, annotate variants, or construct critical editions.` | Yasak işlevlere ait endpoint, route veya UI sıfır; Pinokyo demosu tek tanık ve bağımsız eserler kullanır; related-tools tablosu mevcut | `scope-boundary-audit.md`, related-tools matrix | P002, P004, P009, P013, P015 | `Delta currently focuses on work-level stylometry; no comparative superiority over PhiloEditor is claimed.` |
| CE-04 | `For the preregistered fixture suite under R [version] and stylo [version], Delta reproduced feature lists exactly, distance matrices within 1e-6, and tie-aware nearest-neighbor orderings exactly.` | Anchor, Unicode/locale, culling, segment, tie ve insufficient-feature fixture'ları; feature list birebir; matris farkı `<=1e-6`; tie-aware sıra aynı | `parity-report.json`, raw R outputs, fixture hashes | P006, P007 | `Delta uses stylo as its backend; parity has not been established beyond the reported fixtures.` |
| CE-05 | `On the locked known-author benchmark, Delta obtained macro accuracy [X, 95% CI] under work-grouped evaluation.` | Proje minimumu 5 yazar ve yazar başına 4 bağımsız eser; grouped veya nested CV; segment leakage sıfır; fold içi train-only calibration; bütün confusion, rank, margin ve agreement sonuçları raporlanır | `known-author-benchmark-report.json`, split manifest, confusion matrix | P010 | `The locked benchmark produced [X]; the result does not support a general accuracy or reliability claim.` |
| CE-06 | `On a locked multi-author diachronic benchmark, Delta estimated [effect] between publication-time separation and stylometric distance.` | Proje minimumu 5 yazar, yazar başına 4 bağımsız eser ve en az 3 kronolojik nokta; work-level permutation; calibration ve locked test ayrımı; ilişki claim'i için düzeltilmiş `p<.05` ve CI null değeri dışlar | `diachronic-benchmark-report.json`, chronology manifest | P010, P011 | `The workflow was exercised on a diachronic corpus, but the observed association was inconclusive or heterogeneous.` |
| CE-07 | `Unknown and holdout texts did not influence feature ranking, culling, standardization, parameter selection, or threshold calibration.` | Split kesişimi sıfır; holdout içeriği değişince training feature listesi, mean, standard deviation ve eşikler değişmez; aynı `work_id` iki fold'a girmez | `leakage-audit.json`, fold manifests, invariance report | P006, P010, P011 | `The analysis is transductive and exploratory; it is not predictive validation.` Leakage varsa ilgili benchmark bütünü geçersizdir. |
| CE-08 | `Delta reports parameter stability, not confidence or probability of correctness.` | Grid ve threshold hashli; calibration locked test ve Pinokyo'dan önce; nitel etiket için stability ile doğru benchmark davranışı arasındaki ilişki önceden dondurulmuş protokolü geçer; geçmezse yalnız ham bileşenler | `stability-protocol-v1.json`, calibration report, UI copy audit | P009, P010, P011 | `The interface reports raw parameter-agreement components; these do not estimate correctness.` |
| CE-09 | `Delta surfaces specified corpus imbalances as potential confounds; it does not claim to remove or statistically control them.` | Genre, audience, source, edition, length, adaptation, collection, date certainty ve single-work-period fixture matrisi yüzde 100 beklenen warning veya blocker üretir; temiz fixture'da yanlış blocker sıfır | `confound-fixture-report.json`, corpus-health fixtures | P004, P007, P009, P011 | `Delta displays corpus metadata; automated confound detection for [factor] remains unverified.` |
| CE-10 | `A matched non-candidate control demonstrated that forced-choice Delta still returns a nearest candidate; Delta does not implement open-set rejection.` | En az 5 bağımsız non-candidate control; tamamı raporlanır; none-of-the-above veya dışlama olasılığı üretilmez | `negative-control-report.json` | P009, P010 | `Open-set behavior was not evaluated; all proximity outputs are forced-choice.` |

CE-05 ve CE-06 minimumları evrensel stilometri kuralları değildir. Bu projenin önceden belirlenmiş validation gate'leridir.

## 3. Reproducibility, FAIR ve Operasyon Claim'leri

| ID | Kesin claim, yalnız verified ise | Kanıt ve acceptance gate | Artifact | Ticket | Gate başarısızsa fallback language |
|---|---|---|---|---|---|
| CE-11 | `A non-developer reproduced the archived run from a clean clone under the pinned environment without manual repair.` | Clean clone; manuel kaynak düzeltmesi yok; feature list ve JSON aynı; sayısal fark `<=1e-6`; gerekli veri haklar çerçevesinde erişilebilir | `clean-room-rerun-report.md`, checksums, environment manifest | P012, P015 | `The run is documented for rerun; clean-room reproduction has not been demonstrated.` |
| CE-12 | `Delta exports a FAIR-oriented reproducibility package with machine-readable metadata, provenance, rights, checksums, locked environments, and rerun instructions.` | RO-Crate ve metadata validator hatası sıfır; checksum yüzde 100; VERSION, commit, DOI, SWHID ve site aynı release'i gösterir; Data Availability gerçek inventory ile aynı | `ro-crate-validation.json`, `metadata-consistency-report.json`, release inventory | P001, P012, P015 | `Delta exports a structured reproducibility bundle; persistent identifiers or complete rerun evidence remain incomplete.` |
| CE-13 | `Public artifacts include raw or normalized text only when every relevant rights layer is explicitly permitted.` | Her asset katmanında status ve evidence; public raw için tüm gerekli katmanlar `permitted`; `restricted`, `unknown` ve `permission_required` raw dışarı çıkmaz; Collodi manuel audit tamam | `rights.json`, `DATA-SOURCES.csv`, `rights-audit.md` | P004, P012, P013, P015 | `The public package contains metadata, checksums and permitted derived results only; source texts must be obtained separately.` |
| CE-14 | `In the tested production configuration, application-managed raw and normalized files are deleted after successful export, failed workspaces within 15 minutes, disk exports within one hour, and content-free security logs within seven days.` | Success, failure, cancel, timeout, crash ve restart lifecycle testleri; loglarda corpus ve metadata içeriği sıfır; workspace backup ve snapshot dışında | `retention-test-report.json`, deletion ledger, backup audit | P005, P014, P015 | `Uploads are transient in application-managed storage; exact deletion guarantees have not completed deployment verification.` |
| CE-15 | `Delta is operationally isolated from lda.lemmata.app on the shared VPS through separate service identities, environments, ports, directories, queues, and resource limits.` | Cross-user erişim reddi; load testte LDA error veya restart sıfır; provisional p95 latency artışı `<=20%`; rollback ve iki site smoke test başarılı | `isolation-audit.md`, `load-test.json`, `rollback-log.md` | P014 | `Delta and LDA share one host; service separation is configured, but workload isolation has not passed stress and rollback verification.` |

CE-15 p95 yüzde 20 sınırı P014 baseline ölçümünden önce dondurulacak proje SLO'sudur. Aynı kernel paylaşıldığı için `completely isolated` ifadesi hiçbir zaman kullanılmaz.

## 4. Worked Example, Evaluation, AI ve Development Claim'leri

| ID | Kesin claim, yalnız verified ise | Kanıt ve acceptance gate | Artifact | Ticket | Gate başarısızsa fallback language |
|---|---|---|---|---|---|
| CE-16 | `In the selected rights-audited Collodi corpus, Pinocchio's work-level placement [remained/did not remain] stable across the preregistered parameter grid and leave-one-work-out analyses.` | En az 6 bağımsız eser ve 3 kronolojik nokta; tek Pinokyo tanığı; core/panorama ayrı; rights gate; Pinokyo calibration dışında; grid ve eşikler run öncesi hashli; diff işlevi sıfır | `pinocchio-worked-example/` run package, rights and confound reports | P011, P012, P013 | `An exploratory Collodi example illustrates the workflow; it does not establish Pinocchio as a stylistic turning point or a career-wide shift.` |
| CE-17 | `The release candidate was evaluated through a structured walkthrough by one domain expert and coauthor; [X/6] predefined tasks were completed and all observed defects are reported.` | Hashli altı görev; yardım, hata ve yanlış yorumlar kayıtlı; `all tasks` için 6/6; açık blocker veya critical defect sıfır | `expert-walkthrough-v1.md`, `defect-log.csv` | P015 | `A collaborator performed internal expert QA; no user-study or general usability inference is made.` |
| CE-18 | `Delta's v0.1 analysis runtime does not invoke an LLM or external AI API.` | SBOM, dependency, config, secret ve endpoint taraması; dış ağ kapalı E2E; external AI request sıfır | `runtime-ai-audit.json`, SBOM, egress-denied logs | P001, P002, P014, P015 | `v0.1 exposes no runtime AI feature; complete no-LLM runtime verification remains pending.` |
| CE-19 | `Claude and Codex assisted development. From P001 onward, AI-assisted tickets are linked to PromptEvents with hashes and explicit recording modes.` | P001 sonrası AI-assisted ticket ve commit coverage yüzde 100; hash verification yüzde 100; reconstructed kayıt native diye sunulmaz; gaps raporlanır | `prompt-events.jsonl`, `provenance-coverage.json`, AI disclosure | P001-P015 | `AI tools assisted development; the surviving provenance record is incomplete and reconstructed where indicated.` |
| CE-20 | `Delta was developed through scholarly vibe coding: a literary and digital humanities scholar without prior formal proficiency in Python software development retained ownership of research, method, acceptance, and scientific claims while using AI agents for implementation support.` | İmzalı öz-konumlanma beyanı; tamamlanan P001-P015 ticket'larında human decision/acceptance owner coverage yüzde 100; AI önerisi ile insan kararı ayrı; başarısız ajan koşumları dahil; Barış ledger walkthrough'u; genellenebilirlik iddiası sıfır | `human-decision-ledger.jsonl`, `scholarly-vibe-coding-case-report.md`, provenance coverage, expert checklist | P001-P015 | `AI agents assisted a scholar-led development process; the available record does not support a fuller claim about decision ownership or transferability.` |

## 5. P001 Claim Durum Kaydı

| Claim | Durum | P001 kanıtı | Kalan kapı |
|---|---|---|---|
| CE-12 | `implemented` | Kilitli ortamlar, citation/CodeMeta, checksum ve Run şemaları; `provenance/evidence/P001/report.md` | RO-Crate, gerçek release inventory, persistent identifiers ve P012/P015 clean rerun |
| CE-18 | `implemented` | SBOM, dependency/config/secret taraması; v0.1 bağımlılıklarında runtime LLM istemcisi yok | P002 offline network trace ile P014/P015 production egress audit |
| CE-19 | `implemented` | P001 Ticket, PromptEvent, commit ve recording-mode bağlantısı; exact request hash'i | P002-P015 tam coverage ve final provenance coverage raporu |
| CE-20 | `implemented` | İki HumanDecision kaydı ve P001'de insan/AI rol ayrımı | P002-P015 owner coverage, başarısız koşumların kapsamı ve Barış ledger walkthrough'u |

Bu ara durumlar claim'lerin `verified` olduğu anlamına gelmez. Site ve makale,
ilgili son kapılar geçene kadar her satırın fallback language'ini kullanır.

## 6. Claim Embargoları

- CE-04 geçmeden genel `stylo parity` denmez; yalnız doğrulanan fixture adı verilir.
- CE-11 ve CE-12 geçmeden `reproducible` kanıtlanmış sıfat gibi kullanılmaz. Güvenli ara ifade `reproducibility-oriented` olur.
- CE-08 geçmeden Stable, Partially stable ve Unstable etiketleri yayımlanmaz.
- CE-13 geçmeden Pinokyo corpus'u public downloadable corpus diye sunulmaz.
- CE-15 geçmeden production isolation claim'i kurulmaz.
- CE-17 Barış'ın testi independent usability validation diye sunulmaz.
- CE-20 geçmeden scholarly vibe coding yalnız proje yöntemi ve öz-konumlanma beyanı olarak anlatılır; ampirik development case veya genellenebilir model diye sunulmaz.

Çalışma başlığı kanıt üretilene dek `Reproducibility-Oriented` kullanır. `Reproducible` ancak CE-11 ve CE-12 birlikte geçerse submission öncesinde başlığa alınabilir.

## 7. Site ve Makale Denylist

Şu ifadeler kullanılmaz:

- `the first`, `unique`, `revolutionary stylometry tool`
- `Delta proves or identifies the author`
- `highly accurate`, `reliable` veya `validated accuracy`, locked benchmark olmadan
- `confidence score` veya `probability of correctness`, stability için
- `controls for confounds` veya `removes confounds`
- `FAIR-compliant`, `FAIR-certified` veya `FAIR guarantees quality`
- `fully reproducible`, clean-room ve data-availability kanıtı olmadan
- `completely isolated`, aynı VPS için
- `easy`, `intuitive`, `usable by everyone`, `teachability demonstrated`
- `Pinocchio marks a stylistic turning point`
- `AI-free`, çünkü geliştirmede AI kullanılır
- `every prompt and response is public`
- `no technical or methodological knowledge is needed`
- `AI makes programming expertise unnecessary`
- `any scholar can build reliable software with AI`

Doğrulanabilir ürün cümlesi:

> Run supported stylometric workflows without first learning or writing R or Python code. Delta handles the code while keeping corpus choices, parameters, limitations, and rerun evidence visible.

Bu cümle yalnız desteklenen akışların teknik ön koşulunu tarif eder. General ease, learnability veya methodological competence claim'i değildir.

## 8. Güncelleme Protokolü

Her ticket kapanırken:

1. İlgili CE satırının status değeri güncellenir.
2. Artifact yolu ve hash eklenir.
3. Test komutu ve gerçek sonuç kaydedilir.
4. Gate geçmediyse fallback language site ve makaleye uygulanır.
5. Claim yeni bir veri veya yöntem gerektiriyorsa önce ADR açılır; sonuç görüldükten sonra eşik uydurulmaz.
