# Delta Claude Code Adapter

Bu dosya Claude Code için ince adaptördür. Kanonik proje sözleşmesi değildir.

## Zorunlu Okuma

Her yeni oturumda sırayla oku:

1. START_HERE.md
2. SESSION_HANDOFF.md
3. docs/development/roadmap-P001-P015.md içindeki aktif ticket bölümü
4. Aktif ticket'ın işaretlediği claim, threat ve ADR kayıtları

DEVELOPMENT_CONTRACT.md ve PROJECT_MEMORY.md; mimari/yöntem kararı, belge çelişkisi, P000/P015 kapanışı, release veya START_HERE.md içinde sayılan özel durumlarda tamamen okunur. Bu yönlendirme bağlam tasarrufu içindir; kanonik sözleşmenin otoritesini değiştirmez.

Eski ayrıntılı brief docs/archive/CLAUDE-legacy-brief-2026-07-10.md içindedir. Yalnız tarihsel bağlam için kullan; yeni sözleşmeyle çelişen hükümleri uygulama.

## Başlangıç Davranışı

- Aktif ticket kaydını açmadan kod yazma.
- SESSION_HANDOFF.md içindeki sıradaki işi doğrula.
- Daha önce onaylanmış kararları yeniden sorma.
- Kullanıcı cevap verdikçe PROJECT_MEMORY.md, ilgili ADR ve SESSION_HANDOFF.md dosyalarını güncelle.

## Değişmez Sınırlar

- v0.1 runtime AI/API yok.
- lda.lemmata.app izolasyonu korunur.
- Tool-first makale, Pinokyo merkezli diachronic worked example.
- R stylo ana motor.
- Kesin yazarlık veya nedensellik iddiası yok.
- PhiloEditor benzeri diff, alignment, varyant anotasyonu veya kritik edisyon işlevi yok.
- FAIR-oriented reproducibility package, default no raw text.
- PromptEvent, Ticket, HumanDecision, Commit, ADR ve Run ayrı kaydedilir.
- Scholarly vibe coding kapsamında human decision/acceptance sahipliği AI implementasyon yardımından ayrı kaydedilir.

## Güncel Başlangıç

P004 Metadata, Corpus Inventory, and Rights bütün teknik kapıları geçerek `main`e
alınmıştır. Aktif kayıt `provenance/tickets/P005.json`, dal
`codex/p005-job-lifecycle`, execution brief `prompts/P005-start.md` dosyasındadır.
Session ownership, bounded queue, process lifecycle ve application-managed
retention P005 kapsamındadır; gerçek `stylo`, production isolation, secure erase,
nihai Pinokyo corpus'u veya deployment ekleme.
