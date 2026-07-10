# ADR-0006: Expert Walkthrough Instead of a User Study

**Durum:** Kabul edildi  
**Tarih:** 2026-07-10

## Bağlam

İlk öneri, geliştirme sırasında beş kişilik formative test ve beta sonrasında 12-15 hedef kullanıcıyla usability study yapmaktı. Kullanıcı, katılımcı çalışması yapılmayacağını; ürünü kendisinin geliştireceğini ve Barış Yücesan'ın test edeceğini belirtti.

## Karar

- v0.1 için katılımcılı usability study yapılmaz.
- Oğuz Koran geliştirici ve araştırma lideridir.
- Barış Yücesan release candidate üzerinde structured expert walkthrough ve predefined acceptance tasks uygular.
- Test sonuçları sürümlü checklist ve defect log olarak saklanır.
- Barış proje iş birlikçisi ve olası ortak yazar olduğu için test bağımsız kullanıcı çalışması diye sunulmaz.
- Gözlemler yalnız iç QA ise insan katılımcı bulgusu gibi analiz edilmez.

## İzin Verilen İddialar

- "The release candidate was evaluated through a structured walkthrough by a domain expert."
- "All predefined acceptance tasks were completed" yalnız test kanıtı varsa.
- "The interface was designed for humanities researchers without R or Python expertise."

## Yasaklanan İddialar

- "Delta is easy to use."
- "Usability was validated with target users."
- "General users can interpret the outputs correctly."
- "Teachability was demonstrated."

## Sonuç

Makalenin gücü usability genellemesinden değil; scholar-led design, stylo parity, benchmark, parameter stability, confound audit, reproducibility ve Barış'ın belgeli expert acceptance testinden gelecektir. Daha geniş kullanıcı çalışması sonraki sürüm ve ayrı araştırma olarak yapılabilir.
