# Development Provenance

Bu dizin P001'den itibaren machine-readable geliştirme provenance kayıtlarını tutacaktır.

## Kimlikler

- PE-...: tek PromptEvent
- P000-P015: geliştirme ticket'ı
- HD-...: insan-owned yöntem, claim veya acceptance kararı
- ADR-...: karar kaydı
- Git commit SHA: uygulama değişikliği
- RUN-...: analiz veya test koşumu

## Planlanan Dosyalar

~~~text
provenance/
  prompt-events.jsonl
  prompt-events.schema.json
  human-decision-ledger.jsonl
  human-decision.schema.json
  tickets/
  runs/
  evidence/
  redactions.jsonl
~~~

## PromptEvent İlkesi

Bir ticket birden fazla prompt event içerebilir. Manuel terminal işlemi prompt değildir. Commit sayısı prompt sayısı değildir.

Zorunlu alanlar P001'de JSON Schema ile dondurulacaktır:

- event_id
- captured_at_utc
- provider
- model
- surface
- session_id
- request_sha256
- response_sha256
- ticket_ids
- adr_ids
- commit_ids
- recording_mode
- redaction_status
- result_summary

## HumanDecision İlkesi

Scholarly vibe coding sürecinde AI önerisi ile insan kararı aynı kayıt değildir. P001'de dondurulacak HumanDecision şeması en az şunları tutar:

- decision_id
- decided_at_utc
- ticket_ids ve adr_ids
- decision_owner
- acceptance_owner
- question_or_choice
- ai_assistance_summary
- alternatives
- accepted_option ve rationale
- evidence_required
- status

Bu ledger, Oğuz'un her kod satırını elle yazdığını veya incelediğini iddia etmez. Araştırma, yöntem, claim ve acceptance sorumluluğunun kimde olduğunu gösterir.

Bu predevelopment oturumu tam raw message export'u olmadığı için prompt-events.jsonl içine sonradan exact kayıt olarak yazılmamıştır. Kararlar memory/checkpoints/2026-07-10-predevelopment.md içinde açıkça retrospective etiketiyle saklanmıştır.

P000'ın üç rollü son denetimi de native agent message export'u olarak saklanmamıştır. Sonuç ve bir başarısız agent koşumu `docs/development/p000-closure.md` içinde `summary-only` olarak açıklanır. Bu kayıtlar P001 sonrası native PromptEvent coverage oranına dahil edilmez.
