# Vendored font record

## Inter Variable

- Upstream: `rsms/inter`
- Release path: `v4.1/docs/font-files/InterVariable.woff2`
- License: SIL Open Font License 1.1 (`LICENSE-Inter.txt`)
- Retrieved: 2026-07-16
- WOFF2 SHA-256: `693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3`
- License SHA-256: `262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a`

The workbench embeds this file as a local data URL. It does not request a font
from an external service at runtime.

## Source Sans 3 runtime asset

- Provider: the pinned `streamlit==1.59.1` wheel
- Upstream family: `adobe-fonts/source-sans`
- Upstream font version: Source Sans 3.052 (read from both bundled font name tables)
- License: SIL Open Font License 1.1 (`OFL-1.1`)
- Runtime asset: `SourceSansVF-Upright.ttf.BsWL4Kly.woff2`
- Runtime asset SHA-256: `5f16566f7a40d39b339ad26be151fa5a1ab1f0c2574c7a2e619765584a1acbd8`
- Italic runtime asset: `SourceSansVF-Italic.ttf.Bt9VkdQ3.woff2`
- Italic runtime asset SHA-256: `b4959abc0569392f87c6c6ac612f90e3fe0104d283724189b7d8b6f61af347d3`
- Verified: 2026-07-17
- Upstream license record: <https://github.com/adobe-fonts/source-sans/blob/release/LICENSE.md>

Delta does not copy or separately serve these two files. Streamlit already
ships them in its local frontend bundle, so the body typeface adds no external
request and no second font payload. The hashes above bind this record to the
actual pinned wheel assets used by local and CI verification.
