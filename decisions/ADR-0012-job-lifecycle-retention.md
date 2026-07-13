# ADR-0012: Ephemeral Job Control and Retention Model

**Durum:** Engineering baseline; P005 acceptance veya production retention claim'i değildir

**Tarih:** 2026-07-12

**Kapsam:** P005 session ownership, job state, queue, workspace, cleanup, and retention

## Bağlam

P003 payload'ı güvenli ve bounded biçimde doğrular. P004 yalnız payload-free catalog,
metadata, rights ve inventory state'i taşır. P006 gerçek R worker'ı, P008 ise public
upload-to-run akışını ekleyecektir. P005 bu katmanların arasında, araştırma içeriğini
kalıcı proje geçmişine dönüştürmeden job ownership ve lifecycle sağlamalıdır.

Yalnız Streamlit session state restart, multi-process concurrency ve atomic queue
admission için otorite değildir. Yalnız kriptografik job ID kullanmak da ownership
değildir. Tek `cleaned` state'i farklı retention sürelerini ve terminal sonucu aynı
alana sıkıştırır.

## Karar

- Session capability ve job ID ayrı 256-bit CSPRNG değerleridir.
- Registry yalnız keyed session digest ve content-free operational metadata tutar.
- SQLite, ephemeral runtime root içindeki transactional control store'dur. Corpus,
  filename, scholarly metadata, argv, stdout/stderr, traceback ve absolute path
  saklamaz; permanent project storage değildir.
- Execution state, terminal outcome, cancellation request ve artifact cleanup state
  ayrı alanlardır. Transition'lar expected version/CAS ve operation ID ile idempotent
  uygulanır.
- P005 session-owned staged workspace API sağlar. Bir session bir staged/active lease,
  sistem en fazla dört staged lease taşır. Lease absolute bir saat sonra sona erer.
  Public P004 UI bağlantısı P008'e bırakılır.
- Queue bir running ve en fazla üç queued job'dur. Admission ile allocation tek
  transaction'dır. Queue deadline 15 dakikadır.
- Workspace path yalnız trusted root, owner digest prefix ve server job ID'den oluşur.
  Input label veya metadata path bileşeni değildir. Directory mode 0700, file mode
  0600 olur.
- Success export ancak raw/normalized cleanup doğrulandıktan sonra yayımlanır.
  Failure, cancel, timeout, crash ve abandon cleanup hemen denenir ve 15 dakika üst
  sınırı vardır. Result/export bir saat, allowlisted event/tombstone yedi gün tutulur.
- Startup recovery ile sürekli deadline-driven janitor birlikte çalışır.
- Worker execution shell kullanmaz; sabit argv, temiz environment, kapalı stdin,
  fixed cwd, process group, TERM/KILL/reap ve mandatory finite limit profile ister.
  P005 sentetik fixture worker kullanır; R/stylo ve production limitleri P006/P014'tür.
- Worker monitorü uygulama sürecinde tutulmaz. Ayrı per-job guardian, app-liveness
  pipe ve ayrı POSIX session kullanır. Worker lideri descendants kaybolmadan reap
  edilmez; normal yolda PID/PGID reuse bu sahipli lider kimliğiyle engellenir.
- Worker sonucu guardian'ı serbest bırakmaz. App yalnız job ID, immutable running
  operation reference, terminal SQLite version ve mapped outcome eşleştiğinde ACK
  gönderebilir. ACK yoksa guardian workspace'i temizler ve aynı execution
  reference'a bağlı, imzalı content-free recovery receipt üretir.
- Normal ve emergency reap birlikte başarısız olursa guardian hata verip çıkmaz;
  process-group yokluğu kanıtlanana kadar sahipliği koruyarak reap'i tekrarlar.
- Kullanıcı yüzeyi lifecycle projection hazırlayabilir, fakat P006/P008 öncesi aktif
  Start analysis veya scientific result göstermez.

## Reddedilen Alternatifler

### Module-Level Dictionary ve Streamlit Session State

Reddedildi. Restart recovery, process-safe admission, CAS ve bounded retention
sağlamaz; UI state'i authorization boundary'ye dönüştürür.

### Job ID'yi Bearer Secret Kabul Etmek

Reddedildi. ID sızıntısı cross-session status, cancel veya export erişimine dönüşür.
Ownership ayrı server-side capability ile doğrulanır.

### Yalnız Startup Cleanup

Reddedildi. Uzun süre çalışan süreçte retention deadline'ları aşılır. Sürekli janitor
ve restart recovery birlikte gerekir.

### Tek `cleaned` Terminal State

Reddedildi. Terminal outcome kaybolur ve export/log gibi farklı artifact süreleri
yanlış temsil edilir. Execution ve cleanup orthogonal tutulur.

### P005'te Production Resource Sayıları ve Container Claim'i

Reddedildi. Gerçek R workload P006'dan önce yoktur ve VPS load baseline P014'tedir.
P005 mekanizmayı finite fixture profiles ile sınar; production değerlerini uydurmaz.

### Restart Sonrası Kaydedilmiş PID/PGID ile `killpg`

Reddedildi. PID ve process-group ID yeniden kullanılabilir; uygulama yeniden
başladığında yalnız sayısal kimliğe güvenmek başka bir süreci öldürebilir. Guardian,
orijinal lider child kimliğini reap etmeden tutar ve startup recovery yalnız current
execution reference'a bağlı imzalı receipt ile ilerler.

### Sonuç Mesajını Durable Completion Kabul Etmek

Reddedildi. App sonucu aldıktan sonra SQLite terminal transition'dan önce ölebilir.
Bu nedenle result ve durable ACK ayrı protokol aşamalarıdır.

## Sonuçlar

- SQLite içeriği ve WAL canary taramasına dahildir.
- Staged input API upload-once akışını mümkün kılar, fakat P008 bağlantısına kadar
  public UI payload-free kalır.
- Queue ve cleanup race testleri normal unit testten daha ağırdır; deterministic
  clocks, barriers ve ayrı process fixtures gerekir.
- `deleted`, `cancelled` veya `complete` kullanıcı metni yalnız ilgili doğrulama
  tamamlandığında üretilebilir.
- P005 kapanışı application-managed local evidence'tır. Secure erase, proxy, swap,
  snapshot, backup, cgroup, host isolation ve Delta-LDA isolation P014'te kalır.

## Kanıt Bağlantıları

- `provenance/evidence/P005/architecture-audit.md`
- `provenance/evidence/P005/guardian-app-loss-validation.md`
- `prompts/P005-start.md`
- `provenance/tickets/P005.json`
