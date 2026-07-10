# ADR-0008: Scholar-Led Scholarly Vibe Coding

**Durum:** Kabul edildi  
**Tarih:** 2026-07-10  
**Kullanıcı teyidi:** Oğuz Koran, Delta'yı formal Python uzmanlığı olmadan Claude ve Codex yardımıyla geliştirdiğini ve bu yaklaşımın scholarly vibe coding olarak kaydedilmesini istedi.

## Bağlam

Delta'nın hedef kullanıcısı desteklenen stilometri akışlarını çalıştırmak için önce R veya Python öğrenmek zorunda olmamalıdır. Aynı durum geliştirme sürecinde de anlamlıdır: Delta, alan ve yöntem kararlarını taşıyan bir edebiyat/DBB araştırmacısı tarafından, formal Python yazılım geliştirme uzmanlığı başlangıç koşulu olmadan geliştirilmektedir.

Bu olgu saklanırsa AI-assisted development yalnız teknik bir disclosure'a indirgenir. Abartılırsa “AI herkesin güvenilir bilimsel yazılım üretmesini sağlar” gibi kanıtsız bir genellemeye dönüşür. Bu nedenle scholarly vibe coding açık, sınırlandırılmış ve kanıt kapılı bir geliştirme protokolü olarak tanımlanır.

## Karar

Delta için **scholarly vibe coding**, alan uzmanının bilimsel ve ürün sahipliğini koruduğu, AI ajanlarının kodlama kapasitesinden yararlandığı, evidence-gated bir araştırma yazılımı geliştirme biçimidir.

Başlangıç konumu şu şekilde beyan edilir:

> Delta is being developed by a literary and digital humanities scholar without prior formal proficiency in Python software development, using a scholar-led, evidence-gated form of AI-assisted development that we call scholarly vibe coding.

Bu cümle öz-konumlanma beyanıdır. Kullanıcının hiçbir Python bilgisi olmadığı, süreçte hiçbir şey öğrenmediği veya herkesin aynı sonucu elde edeceği anlamına gelmez.

## Sorumluluk Ayrımı

Oğuz Koran'ın devredilemez sorumlulukları:

- Araştırma problemi ve ürün amacı
- Corpus seçimi, hak ve kaynak kararları
- Kanonik stilometri yöntemi ve yorum sınırları
- Acceptance kriterleri ve claim kapsamı
- Pinokyo/PhiloEditor görev sınırı
- Nihai ürün, release ve makale onayı

Claude ve Codex'in destekleyici görevleri:

- Kod, test, şema ve dokümantasyon taslağı üretme
- Alternatif mimari ve risk önerme
- Hata ayıklama, fixture hazırlama ve otomatik kontrol çalıştırma
- Claim, güvenlik ve yöntem tutarlılığı için adversarial review
- Yapılan işi PromptEvent, Ticket, HumanDecision, Commit, ADR ve Run kayıtlarına bağlama

AI ajanları kendi ürettikleri kodun bilimsel geçerliliğine tek başına karar veremez. Bir ajan çıktısı ancak otomatik test, doğrudan `stylo` parity, bağımsız fixture, claim gate ve gerektiğinde başka ajan denetimiyle kabul edilir. Oğuz'un her satırı elle okuyabilmesi şart koşulmaz; hangi kanıtın yeterli olduğuna ve ürünün ne iddia edeceğine insan karar verir.

## Ürün Vaadi Ayrımı

İki iddia birbirine karıştırılmaz:

1. **Yapısal no-code iddiası:** Desteklenen kullanıcı akışları R veya Python kodu yazmayı ya da yapılandırmayı gerektirmez.
2. **Öğrenme eşiği iddiası:** Kullanıcı Delta'yı kullanmaya başlamak için önce R veya Python öğrenmek zorunda değildir; yöntemsel kavramları yine anlaması ve yorum sorumluluğunu taşıması gerekir.

İkinci iddia “herkes için kolay”, “hiç teknik bilgi gerekmez” veya “öğrenilebilirliği kanıtlandı” anlamına gelmez. Arayüz yöntemi öğretici biçimde açıklar, fakat pedagojik etki v0.1'de genellenebilir bir kullanıcı çalışmasıyla kanıtlanmış sayılmaz.

## Makaledeki Rol

Scholarly vibe coding, Delta makalesinin ana ürün tezinin yerine geçmez. İkincil ve refleksif bir yöntem katkısıdır:

- Ana katkı, uncertainty-aware ve reproducibility-oriented stylometry workbench'tir.
- Scholarly vibe coding, bu workbench'in bir alan uzmanı tarafından nasıl geliştirildiğini ve bilimsel sahipliğin nasıl korunduğunu açıklar.
- Makalede yöntem/provenance altında ayrı bir alt bölüm ve sınırlılıklar kısmında öz-konumlanma beyanı bulunur.
- Prompt ve ticket kayıtları yeterli coverage üretirse süreç ampirik bir development case olarak raporlanabilir.
- Kayıt yetersizse yalnız disclosure ve refleksif yöntem notu olarak kalır; başarı veya genellenebilirlik iddiası kurulmaz.

## Kanıt Protokolü

P001'den itibaren aşağıdakiler tutulur:

- Oğuz'un başlangıç beceri ve rol beyanı
- Her ticket için human-owned decision ve acceptance alanları
- AI tarafından önerilen ve insan tarafından kabul/reddedilen önemli seçenekler
- PromptEvent, ticket, commit, test ve ADR bağlantıları
- AI çıktısında bulunan hatalar, başarısız ajan koşumları ve düzeltmeler
- Hangi kararın alan uzmanlığına, hangi kararın otomatik teste, hangisinin dış kaynağa dayandığı
- P015 sonunda provenance coverage ve human-decision ledger özeti

## Sonuçlar

- `without learning R or Python` mutlak denylist olmaktan çıkar; sınırlandırılmış ürün açıklaması olarak kullanılabilir.
- `no prior R or Python coding is required for the supported workflows` tercih edilen site dilidir.
- “No knowledge is required”, “any scholar can build reliable software with AI” veya “AI replaced programming expertise” ifadeleri yasaktır.
- P001'de repository topolojisi için açılacak sonraki karar ADR-0009 olur.
- Scholarly vibe coding ileride ayrı bir yöntem makalesine dönüşebilir; Delta v0.1 makalesinde tool-first odak korunur.
