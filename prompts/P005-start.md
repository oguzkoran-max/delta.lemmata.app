# P005 Execution Brief

**Kayıt türü:** Agent-prepared, human-owned ticket execution brief

**PromptEvent değildir:** Kullanıcının native devam isteği ayrı PromptEvent içinde
hash ile kayıtlıdır. Bu dosya, onaylı roadmap ve güvenlik sözleşmesinin teknik
açılımıdır; native kullanıcı mesajı gibi sunulmaz.

```text
P005: Job Lifecycle, Isolation, and Retention

START_HERE.md ve SESSION_HANDOFF.md dosyalarını oku. Ardından roadmap'teki yalnız
P005 bölümünü, claim CE-14 ve CE-15'i, threat SEC-07, SEC-09, SEC-11, SEC-12 ve
SEC-13'ü, ADR-0012'yi, P003 secure-ingestion kapanış sınırını ve P004 payload-free
Review sınırını incele. Daha önce onaylanmış ürün kararlarını yeniden sorma.

Önce P005 Ticket ve native devam isteğine bağlı PromptEvent kaydını doğrula. Sonra:

1. Versioned `job-policy-v1` kur. Bir worker, en fazla üç queued job, en fazla dört
   global staged lease ve session başına bir staged/active job sınırını atomik uygula.
   Queue veya staging reddi job ID, workspace, process ya da log ayırmasın.
2. Job ID ile ownership'i ayır. Job ve session capability en az 256-bit CSPRNG ile
   server-side üretilsin; control store yalnız keyed owner digest tutsun. Her status,
   cancel, result, export ve cleanup erişimi ownership doğrulasın. Unknown ve
   unauthorized aynı content-free hata biçimine dönsün.
3. Payload-free ve süreli bir SQLite control store kur. Store corpus, filename,
   metadata, argv, stdout/stderr, traceback veya absolute path tutmasın. Bu store
   permanent project history değildir; tombstone ve event kayıtları en çok yedi gün
   sonra silinsin.
4. Execution outcome ile artifact lifecycle'ı ayır. Staged, queued, running ve
   terminal outcome; cancellation request; input/work/result/export cleanup durumu;
   immutable deadlines ve optimistic version/CAS tek bir deterministic sözleşmede
   olsun. Illegal transition ve ikinci terminal outcome fail-closed olsun.
5. P003 tarafından doğrulanmış payload'ı kullanıcı adı veya filename path'e katmadan
   session-owned staged workspace'e güvenli biçimde materialize eden API kur.
   Staged lease bir saatlik absolute TTL taşısın ve public P004 UI'ya P006/P008'den
   önce bağlanmasın. Streamlit session_state payload otoritesi olmasın.
6. Trusted root altında server-generated job dizinleri ve `input`, `work`, `result`,
   `export`, `control` alt dizinleri oluştur. Directory mode 0700, file mode 0600,
   symlink/hardlink/path replacement fail-closed olsun; cleanup trusted root dışına
   dokunamasın.
7. FIFO queue admission'ı SQLite transaction içinde kapasite kontrolüyle birleştir.
   Running bir, queued üç sınırını concurrency testinde koru. Queue wait deadline'ı
   15 dakika olsun; deadline mevcut job için sonradan uzatılmasın.
8. Sabit argv, shell=False, temiz environment, kapalı stdin, belirli cwd ve yeni
   process group kullanan generic ProcessController kur. Her worker profile finite
   wall, CPU, RAM ve PID limitleri vermeden çalışamasın. P005 yalnız sentetik fixture
   worker kullanır; gerçek R/stylo adapter ve production sayıları P006/P014'tedir.
9. Cancel ve timeout'ta process group'a TERM, kısa grace sonrası KILL uygula ve reap
   doğrulanmadan cancelled/timed_out gösterme. Worker completion, cancel, timeout ve
   janitor yarışları yalnız bir terminal outcome üretsin.
10. Startup recovery ile sürekli deadline-driven janitor kur. Success export'u ancak
    raw/normalized cleanup doğrulandıktan sonra görünür olsun. Failed, cancelled,
    timed-out, crashed ve abandoned workspace hemen temizlenmeye çalışılsın ve en
    geç 15 dakikada yok olsun. Result/export en çok bir saat, content-free event ve
    deletion tombstone en çok yedi gün kalsın.
11. Deletion ledger yalnız stable event code, job reference digest, UTC, reason,
    file count ve byte count tutsun. Canary corpus metni, filename, metadata, path,
    stdout/stderr veya traceback hiçbir log, SQLite/WAL, başka session, error yüzeyi
    ya da export içinde görünmesin.
12. Beginner-facing lifecycle projection ve English string contract hazırla, fakat
    P006/P008 tamamlanmadan public Start analysis veya sahte success/result açma.
    Queued, running, cancelling, failed, cancelled, expired ve busy durumları teknik
    jargon, doğrulanmamış yüzde/ETA veya full job ID göstermesin.
13. State matrix, idempotency, race, cross-session denial, queue saturation, staged
    expiry, symlink/rename swap, nested child cancellation, timeout, simulated OOM,
    worker crash, restart recovery, fake-clock retention ve canary taramalarını ekle.
    Measured source için yüzde 100 statement/branch coverage kapısını koru.
14. Başarısız denemeleri, policy hash'ini, test sonuçlarını ve platform sınırlarını
    P005 evidence paketinde sakla. Exact-commit clean-clone, Linux CI ve adversarial
    yeniden denetim geçmeden P005'i complete yapma.

P005 kapanışında production CE-14 veya CE-15'i verified yapma. Secure/forensic erase,
swap/snapshot/backup/proxy temizliği, cgroup/container isolation, Delta-LDA host
izolasyonu, gerçek R/stylo güvenliği, scientific result, dağıtık queue, kullanıcı
hesabı, permanent project history, deployment veya Launch Stylometry uygulama.
```
