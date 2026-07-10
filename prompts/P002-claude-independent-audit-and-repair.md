# P002 Claude Independent Audit and Repair Brief

**Belge türü:** Human-reviewed execution brief

**Amaç:** Claude Code'un tamamlanmış P002 workbench shell'ini bağımsız olarak
denetlemesi, kanıtlanmış eksikleri gidermesi ve Codex'in sonradan inceleyebileceği
ayrı bir Git branch'i bırakması.

**Bu dosya PromptEvent değildir:** Claude Code'a gönderilen gerçek launch mesajı
ayrıca native request olarak hash'lenmeli ve yeni PromptEvent kaydına bağlanmalıdır.

## Claude Code'a Gönderilecek Tek Satır

```text
prompts/P002-claude-independent-audit-and-repair.md dosyasını eksiksiz oku ve uygula. Önce hiçbir dosyayı değiştirmeden bağımsız çoklu-ajan denetimini tamamla; ardından yalnız kanıtlanmış P002 eksiklerini ayrı branch üzerinde düzelt, bütün test ve FAIR kapanış adımlarını çalıştır. Daha önce onaylanmış ürün kararlarını yeniden sorma; yalnız kanonik belgeler arasında çözülemeyen gerçek bir çelişki varsa dur.
```

---

## 1. Rolün

Sen Delta'nın önceki uygulayıcısı değilsin. Bağımsız bir senior product reviewer,
Streamlit/Python engineer, accessibility reviewer, digital humanities method
reviewer ve FAIR/provenance auditor olarak çalışacaksın.

Codex'in P002 tercihlerini doğru kabul etme. Her tercihi kanıtla veya eleştir.
Bununla birlikte yalnız kişisel zevke dayanarak yeniden tasarım yapma. Bir değişiklik
şu dört temelden en az birine dayanmalıdır:

1. Kabul ölçütü ihlali
2. Kullanılabilirlik veya erişilebilirlik sorunu
3. Kod, güvenlik ya da bakım riski
4. Yanlış, belirsiz veya epistemik açıdan sakıncalı içerik

Görevin yalnız rapor yazmak değildir. Kanıtlanmış ve P002 kapsamı içinde kalan
eksikleri düzeltmek, yeniden doğrulamak ve iz bırakmaktır.

## 2. İlk Okuma Paketi

Başka dosyaya geçmeden önce sırayla oku:

1. `START_HERE.md`
2. `SESSION_HANDOFF.md`
3. `DEVELOPMENT_CONTRACT.md` içindeki ürün, FAIR, claim ve ticket kuralları
4. `PROJECT_MEMORY.md` içindeki P002 kapanışı ve onaylanmış kararlar
5. `provenance/tickets/P002.json`
6. `provenance/evidence/P002/report.md`
7. `provenance/evidence/P002/browser-audit.json`
8. `provenance/evidence/P002/accessibility-report.json`
9. `provenance/evidence/P002/network-trace.json`
10. `docs/research/claim-evidence-matrix.md` içinde CE-01, CE-18 ve CE-20
11. `docs/security/threat-model.md` içinde SEC-14 ve EPI-13
12. `decisions/ADR-0001-product-and-paper.md`
13. `decisions/ADR-0003-fair-provenance-and-memory.md`
14. `decisions/ADR-0008-scholarly-vibe-coding.md`
15. P002 source ve test dosyaları

`docs/archive/` aktif talimat değildir. Tarihsel bir çelişkiyi anlamak gerekmedikçe
okuma. P003 veya sonraki ticket belgelerini P002'ye özellik taşımak için kullanma.

## 3. Değişmez Sınırlar

- Site v0.1'de yalnız İngilizcedir.
- İlk ekran marketing landing page değil, gerçek workbench olmalıdır.
- Üç amaç değişmez: Text Proximity, Group Comparison, Style Over Time.
- Guided ve Research ayrımı korunur.
- Runtime AI, harici LLM/API, analytics, login ve permanent storage eklenmez.
- R `stylo` ana hesaplama motorudur; fakat P002'de çalıştırılmaz.
- Secure ingestion P003'tür. P002 denetiminde upload aktif hale getirilmez.
- Scientific calculation, results, charts, Pinocchio data ve export uygulanmaz.
- `lemmata.app` içindeki `Launch Stylometry` bağlantısına dokunulmaz.
- PhiloEditor benzeri diff, alignment, variant annotation veya critical edition eklenmez.
- Kesin authorship, confidence/probability, causality, universal ease veya
  `FAIR-certified` dili kullanılmaz.
- Desteklenen iş akışlarında R/Python kod eşiğini kaldırma vaadi korunur; yöntem
  bilgisi ve yorum sorumluluğunun araştırmacıda kaldığı açık olmalıdır.
- Önceki P002 evidence dosyalarının üstüne yazılmaz. Yeni denetim ayrı alt klasörde tutulur.
- Kullanıcıya ait veya başka projelere ait değişiklik geri alınmaz.

## 4. Git Güvenliği

1. Delta repository kökünde olduğunu doğrula.
2. `git status --short` çalıştır.
3. Beklenmeyen değişiklik varsa hiçbir şeyi silme veya geri alma; kullanıcıya bildir.
4. Çalışma ağacı temizse güncel `main` üzerinden
   `claude/p002-independent-audit` branch'ini oluştur.
5. Main'e merge etme, force-push yapma ve history rewrite uygulama.
6. Bütün düzeltmeleri bu branch'te commit et.
7. Codex'in sonradan karşılaştırabilmesi için final branch ve commit kimliklerini bildir.

## 5. Çoklu-Ajan Denetim Tasarımı

Toplam bütçe en fazla **90.000 token**. Önce read-only fan-out, sonra tek sentez ve
uygulama turu yap. Aynı dosyaları her ajana bütünüyle kopyalama; görevine gereken
minimum bağlamı ver.

Altı bağımsız rol:

1. **Product and workflow reviewer, 8k:** bilgi mimarisi, araştırma akışı,
   beginner/expert dengesi, disabled aşamaların dürüstlüğü.
2. **Visual and responsive reviewer, 8k:** profesyonel görünüm, hiyerarşi,
   yoğunluk, mobil/laptop/desktop davranışı, Lemmata ailesiyle akrabalık.
3. **Accessibility reviewer, 8k:** keyboard, focus, names, roles, headings,
   contrast, disabled controls, zoom ve reduced-motion sınırı.
4. **Python and Streamlit reviewer, 10k:** state/rerun davranışı, modülerlik,
   HTML escaping, config, testability, dependency ve bakım riski.
5. **Content and DH methodology reviewer, 8k:** İngilizce açıklık, yeni başlayan
   kullanıcı, stilometri kavramları, method boundaries ve yasaklı claims.
6. **Security, privacy and FAIR reviewer, 8k:** runtime boundary, telemetry,
   external requests, health output, provenance completeness ve kanıt dürüstlüğü.

Sentez, uygulama ve tekrar doğrulama için en fazla 40k kullan. Bir alt-ajanın
çıktısını diğerine doğru kabul ettirme. Çelişkileri ana ajan kanıtla çözsün.

Alt-ajan altyapısı kullanılamıyorsa bu altı rolü sırayla ve birbirinden bağımsız
notlarla uygula. Bütçeyi artırma.

## 6. Faz 1: Salt Okur Denetimi

Bu faz tamamlanmadan dosya değiştirme.

Her bulguyu şu alanlarla kaydet:

- `finding_id`
- `review_area`
- `severity`: P0, P1, P2 veya P3
- `type`: defect, risk, content, accessibility, visual veya deferred-feature
- `evidence`: dosya/satır, DOM gözlemi, screenshot veya test
- `user_impact`
- `recommended_fix`
- `scope`: fix-now veya defer

Şiddet tanımları:

- **P0:** güvenlik, veri sızıntısı, çalışmayan uygulama veya ciddi bilimsel yanıltma
- **P1:** ana akışı, erişilebilirliği veya kabul ölçütünü bozan hata
- **P2:** profesyonel kaliteyi, açıklığı, bakımı veya responsive davranışı belirgin azaltan sorun
- **P3:** tercihe dayalı cila veya sonraki ticket önerisi

P003/P008/P009/P014 kapsamındaki eksikleri P002 kusuru gibi gösterme. Bunları
`deferred-feature` olarak doğru ticket'a yönlendir.

## 7. Denetim Mercekleri

### 7.1 Ürün ve Akış

- İlk viewport'ta Delta markası, amaç seçimi ve sonraki aşamaya dair bağlam açık mı?
- Üç purpose arasındaki fark, stilometri bilmeyen bir araştırmacı tarafından
  anlaşılabilir mi?
- Guided ve Research adları farklı kontrol düzeylerini doğru anlatıyor mu?
- Kullanıcı, kilitli corpus alanını bozuk özellik sanabilir mi?
- Experiment map hem masaüstünde hem mobilde taranabilir mi?
- Evidence panel, Delta'nın ayırt edici yöntemsel değerini erken fakat ölçülü gösteriyor mu?
- Arayüz bir SaaS landing page'e veya dekoratif card koleksiyonuna dönüşüyor mu?

### 7.2 Görsel Tasarım

- Sessiz, akademik ve operasyonel bir workbench hissi var mı?
- Başlık boyutları panel bağlamına uygun mu?
- Kart içinde kart, gereksiz yuvarlaklık, gradient, tek renk hakimiyeti veya
  dekoratif görsel kalabalık var mı?
- Teal, coral, amber ve blue vurgu renkleri anlamlı ve ölçülü mü?
- 1440x1000, 1280x800, 390x844 ve 360x800 boyutlarında metin, badge, segmented
  control ve columns taşmadan çalışıyor mu?
- Yüzde 200 browser zoom altında ana akış kullanılabilir mi?
- Hover/focus/disabled durumları profesyonel ve ayırt edilebilir mi?

### 7.3 Erişilebilirlik

- Tab, Shift+Tab, Arrow, Space ve Enter ile ana kontrol akışı kullanılabiliyor mu?
- Görünür her kontrolün accessible name ve state'i var mı?
- Heading sırası ve custom HTML heading role'leri tutarlı mı?
- Focus görünür mü ve sticky/header katmanı tarafından örtülüyor mu?
- Renk kontrastı WCAG AA hedefiyle uyumlu mu? Otomatik ölçüm yoksa uyum iddiası kurma.
- Disabled file input ve action'lar screen reader için anlaşılır mı?
- Mobil sidebar açma/kapama kontrolü isimli ve erişilebilir mi?
- Bu denetimi full WCAG certification gibi sunma.

### 7.4 Kod ve Mimari

- User-facing copy gerçekten merkezi registry'den mi geliyor?
- String registry gereksiz karmaşık mı veya key drift riski taşıyor mu?
- `public_health` yalnız allowlisted alanları mı döndürüyor?
- Custom HTML tüm dinamik değerleri escape ediyor mu?
- Streamlit rerun'larında purpose ve mode state'i deterministik mi?
- Source ile tests arasında yalnız implementation detail'e kilitlenen kırılgan test var mı?
- Gereksiz abstraction, dependency veya global side effect var mı?
- `.streamlit/config.toml` privacy ve deployment sınırlarıyla uyumlu mu?
- Type hints, naming, module ownership ve error boundaries profesyonel mi?
- App başlangıç yolu ve package import davranışı temiz checkout'ta çalışıyor mu?

### 7.5 İçerik ve Yöntem

- Bütün görünür metin İngilizce, kısa ve doğal mı?
- Stilometri bilmeyen kullanıcı için açıklayıcı, fakat tutorial duvarına dönüşmeden
  point-of-need açıklama sağlıyor mu?
- Text Proximity authorship proof gibi okunuyor mu?
- Group Comparison corpus/genre/period/source/edition confound sınırını açıklıyor mu?
- Style Over Time ageing, maturation, turning point veya causality iddiasına kayıyor mu?
- Guided/Research açıklamaları henüz uygulanmamış metric veya sonucu vaat ediyor mu?
- `reproducible`, `confidence`, `validated`, `easy`, `no knowledge needed`,
  `identify/find the author`, `FAIR-compliant/certified` gibi kanıtsız dil var mı?
- FAIR-oriented ifade açık mı ve kalite sertifikası gibi okunuyor mu?

### 7.6 Güvenlik, Gizlilik ve FAIR

- Runtime AI, analytics, auth, remote storage veya external endpoint dependency'si var mı?
- Streamlit telemetry gerçekten kapalı mı?
- Sağlık/build görünümü path, environment dump veya secret sızdırabilir mi?
- P002 shell outbound network kapalıyken açılıyor mu?
- Önceki başarısızlıklar ve sınırlamalar korunmuş mu?
- Ticket, PromptEvent, HumanDecision, Run ve commit bağlantıları doğru mu?
- Summary-only kayıt native transcript gibi sunuluyor mu?
- Ekran görüntüsü, test ve hash kayıtları gerçek dosyalarla eşleşiyor mu?

## 8. Faz 2: Sentez ve Karar

Altı raporu birleştir. Duplicate bulguları tekilleştir. Her bulguyu kanıta karşı
yeniden kontrol et. Sonra:

- P0/P1 bulgularını mutlaka düzelt.
- P002 içinde kalan, düşük riskli ve kanıtlı P2 bulgularını düzelt.
- Ürün kapsamını değiştiren veya P003+ özelliği isteyen bulguları defer et.
- Yalnız estetik tercih olan P3 maddeleri için kod değiştirme.
- Kanonik belgeler arasında gerçek çelişki yoksa kullanıcıya soru sorma.
- Bulgu yoksa sırf commit üretmek için refactor veya redesign yapma.

Uygulamadan önce kısa bir fix matrix oluştur: finding, action, file, test, expected
evidence. Bu matrisi review evidence klasörüne kaydet.

## 9. Faz 3: Uygulama Kuralları

- Değişiklikleri küçük, anlaşılır ve P002 sınırında tut.
- Mevcut Streamlit ve proje pattern'lerini kullan.
- Yeni dependency yalnız mevcut araçlarla güvenilir çözüm mümkün değilse ekle;
  lockfile ve gerekçeyi kaydet.
- User-facing yeni metin yalnız English registry'ye eklenir.
- Fake data, fake result, placeholder scientific metric veya uydurma chart ekleme.
- Çalışmayan özelliği enabled gösterme.
- Eski evidence dosyalarını değiştirme; review evidence yeni klasöre gider.
- Her düzeltme için riskle orantılı test ekle veya güncelle.

## 10. Faz 4: Zorunlu Doğrulama

En az şu kontrolleri çalıştır:

1. `./scripts/verify.sh`
2. Run artifact hash consistency
3. Streamlit shell smoke test
4. Browser audit: 1440x1000, 1280x800, 390x844, 360x800
5. Yüzde 200 zoom altında kritik akış
6. Keyboard navigation ve visible focus
7. Accessible names, roles, headings ve disabled states
8. Copy snapshot ve denylist
9. External asset/request inspection
10. Egress-denied shell smoke test
11. Before/after screenshot comparison
12. Yeni Git klonunda bootstrap, verify ve clean status

Bir test başarısız olursa sonucu sakla, nedeni düzelt ve tam kapıyı yeniden çalıştır.
Başarısız ilk sonucu rapordan silme.

## 11. FAIR-Oriented Review Paketi

Önceki P002 artifact'larına dokunmadan şurayı oluştur:

```text
provenance/evidence/P002/claude-independent-review/
  report.md
  findings.json
  fix-matrix.md
  test-summary.json
  before-after.md
  screenshots/
```

Zorunlu kayıtlar:

- Claude Code'a gönderilen gerçek native request için yeni PromptEvent
- Bu audit kararını `HD-20260710-0005` ile ilişkilendirme
- Her test/rerun için Run kaydı
- Bulgu sıfırsa bile review report
- Başarısız denemeler ve geri alınan yaklaşım listesi
- Uygulanan ve defer edilen her bulgunun son durumu
- Dosya hash'leri ve clean-clone sonucu

Kod değiştiyse iki commit kullan:

1. `P002: apply Claude independent audit fixes`
2. `P002: close Claude review evidence`

İlk commit'i clean clone'da test et. İkinci commit'te PromptEvent/Ticket/Run/handoff
bağlantılarını kapat. P002 Ticket'taki eski acceptance evidence'i silme; yeni review
kanıtını ekle. P002'yi ancak P0/P1 açık bulgu kalmadığında complete tut.

Kod değişmediyse tek commit yeterlidir:

`P002: record Claude independent audit`

Main'e merge etme. Branch'i Codex denetimine hazır bırak.

## 12. Puanlama Rubriği

Kanıta dayalı 100 puanlık son rubric:

- Product/workflow: 20
- Visual/responsive design: 15
- Accessibility: 15
- Python/Streamlit quality and tests: 20
- Content and epistemic boundaries: 15
- Security, privacy and FAIR provenance: 15

Review gate ancak şu koşullarda geçer:

- Toplam en az 90/100
- Açık P0 veya P1 sıfır
- P002 acceptance suite tam pass
- Clean-clone rerun pass
- Runtime AI/analytics/login/storage/external request sıfır
- Deferred maddeler doğru sonraki ticket'a bağlı
- Kanıtsız professional, accessible, reproducible veya easy claim'i yok

Puanı yükseltmek için bulgu gizleme. Gate geçmezse açıkça `not accepted` yaz.

## 13. Final Yanıt Formatı

Kullanıcıya Türkçe ve teknik olmayan açık bir özet ver:

1. Hüküm ve puan
2. En önemli bulgular, önem sırasıyla
3. Düzeltilenler
4. Bilinçli olarak sonraya bırakılanlar ve ticket'ları
5. Çalıştırılan testler ve gerçek sonuçları
6. Branch ve commit kimlikleri
7. Review evidence klasörü
8. Codex'in özellikle yeniden denetlemesi gereken noktalar

“Her şey mükemmel” deme. Bulgu yoksa bile denetim kapsamını ve test edilmeyen
alanları belirt. Kullanıcıdan terminal komutu çalıştırmasını isteme; yapabildiğin
bütün işlemleri kendin tamamla.
