# Collodi demo corpus access notice

## Public contents and access boundary

This public evaluation overlay provides source metadata, cleaning metadata,
document hashes, the deterministic request builder, and the derived canonical
analysis request. It does not redistribute the three cleaned full texts.

The corpus lock authorises internal analysis and publication of derived
numerical outputs, while public redistribution of the cleaned texts remains
conditional. The omission is therefore an explicit rights-preserving access
condition. It is not an undocumented missing-data decision.

## Source witnesses

| Document | Public source | Clean SHA-256 | Profile tokens |
|---|---|---|---:|
| *Occhi e nasi* | Italian Wikisource, <https://it.wikisource.org/wiki/Occhi_e_nasi> | `3ba9406ba6d8b20cc65c2505bbc8833bbecb2b242b87c1ae7c091624cb43332b` | 47,383 |
| *Le avventure di Pinocchio* | Project Gutenberg 52484, <https://www.gutenberg.org/ebooks/52484> | `c71c5c87c2a7ca73db6358353de8b9e19680a0b05279cc98707bbfd068181480` | 40,688 |
| *Storie allegre* | Italian Wikisource, <https://it.wikisource.org/wiki/Storie_allegre> | `2b4c89804ddf1abc29172d175e0b337e9af9327c7def4405c63cbb850bc8d65d` | 36,584 |

The first-publication years and audience or genre labels in the metadata are
documentary candidates only. They are not variables for chronological,
periodising, causal, or population-level inference.

## Reproduction

A researcher with lawful access to the listed witnesses can apply the
documented cleaning decisions and run
`execution/scripts/build_demo_worker_request.py`. The reconstructed canonical
request must have SHA-256
`0eb1c53ca5e1f930cd7a331cf13b6b090cf68083b8a16a0bb846c496160fe5f0`.

The public workflow executes that immutable derived request in the pinned
Delta container and compares it with an independent direct-R `stylo` path.
The numerical result and parity evidence are publishable only if all four MFW
conditions pass the preregistered checks.

## Known overlap

The corpus audit found one shared distinct exact 10-gram between *Occhi e
nasi* and *Storie allegre*. It was retained and disclosed. Consequently, no
statistical-independence claim is permitted.
