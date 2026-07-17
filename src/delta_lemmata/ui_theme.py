"""Delta's restrained, accessible workbench visual system."""

from base64 import b64encode
from importlib.resources import files

_INTER_WOFF2 = b64encode(
    files("delta_lemmata").joinpath("data/fonts/InterVariable.woff2").read_bytes()
).decode("ascii")

_FONT_FACE = f"""
<style>
@font-face {{
  font-family: "Inter";
  src: url("data:font/woff2;base64,{_INTER_WOFF2}") format("woff2");
  font-style: normal;
  font-weight: 100 900;
  font-display: swap;
}}
</style>
"""

APP_CSS = (
    _FONT_FACE
    + """
<style>
:root {
  --delta-ink: #1a1a1a;
  --delta-control-ink: #31333f;
  --delta-muted: #5c5c5c;
  --delta-tertiary: #6f6f6f;
  --delta-control-line: #6f7d78;
  --delta-line: #e2e5e4;
  --delta-soft-line: #eef0ef;
  --delta-canvas: #f8f9fa;
  --delta-family-canvas: #f8faf9;
  --delta-paper: #ffffff;
  --delta-sidebar: #f0f2f6;
  --delta-mint: #e8f5f0;
  --delta-mint-strong: #c5e8dc;
  --delta-mint-accent: #5dcaa5;
  --delta-mint-soft: #f4faf7;
  --delta-focus: #0f6e56;
  --delta-teal: #0f6e56;
  --delta-teal-dark: #0a5443;
  --delta-coral: #d85a30;
  --delta-coral-text: #a33d1c;
  --delta-coral-soft: #fef0eb;
  --delta-amber: #b8860b;
  --delta-amber-text: #6b4d00;
  --delta-amber-soft: #fdf6e3;
  --delta-blue: #185fa5;
  --delta-blue-soft: #e8f0fa;
  --delta-purple: #7c3aed;
  --delta-purple-soft: #f3eefe;
  --delta-slate: #5e6f86;
}

html,
body,
[class*="css"] {
  font-family: "Source Sans Pro", "Source Sans 3", -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
}

h1,
h2,
h3,
.delta-brand-name,
.delta-entry h1 {
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

[data-testid="stAppViewContainer"] {
  background: var(--delta-canvas);
}

[data-testid="stMainBlockContainer"] {
  max-width: 1240px;
  padding-top: 1.4rem;
  padding-bottom: 2rem;
}

[data-testid="stHeader"] {
  display: none;
}

#MainMenu,
footer,
[data-testid="stAppDeployButton"] {
  display: none;
}

[data-testid="stSidebar"] {
  background: var(--delta-sidebar);
  border-right: 1px solid var(--delta-soft-line);
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  color: var(--delta-ink);
}

[data-testid="stSidebar"] [data-testid="stExpander"] {
  border-color: var(--delta-line);
  border-radius: 6px;
}

.delta-sidebar-guide {
  margin-top: 1.2rem;
}

.delta-sidebar-title {
  display: block;
  margin: 0 0 0.45rem;
  color: var(--delta-ink);
  font-size: 1.15rem;
  line-height: 1.25;
}

.delta-sidebar-guide > p,
.delta-sidebar-parameters p {
  margin: 0;
  color: var(--delta-muted) !important;
  font-size: 0.88rem;
  line-height: 1.5;
}

.delta-sidebar-guide ol {
  margin: 0.9rem 0 1rem;
  padding-left: 1.3rem;
  color: var(--delta-ink);
}

.delta-sidebar-guide li {
  margin: 0.45rem 0;
  padding-left: 0.2rem;
  font-size: 0.88rem;
  line-height: 1.4;
}

.delta-sidebar-guide li::marker {
  color: var(--delta-teal);
  font-weight: 750;
}

.delta-sidebar-parameters {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--delta-soft-line);
}

.delta-sidebar-parameters strong {
  display: block;
  margin-bottom: 0.35rem;
  color: var(--delta-teal) !important;
  font-size: 0.88rem;
}

.delta-progress {
  width: 100%;
  height: 8px;
  overflow: hidden;
  margin: 0.45rem 0 0.9rem;
  border-radius: 4px;
  background: var(--delta-paper);
}

.delta-progress-fill {
  display: block;
  width: 50%;
  height: 100%;
  background: var(--delta-teal);
}

.delta-header {
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 0 1rem;
  border-bottom: 1px solid var(--delta-soft-line);
  margin-bottom: 1rem;
}

.delta-brand {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.delta-mark {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--delta-teal);
  color: #ffffff;
  border-radius: 6px;
  font-size: 1.55rem;
  font-weight: 700;
  line-height: 1;
}

.delta-brand-name {
  color: var(--delta-ink);
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1.2;
}

.delta-brand-subtitle,
.delta-build-meta {
  color: var(--delta-muted);
  font-size: 0.82rem;
  line-height: 1.35;
}

.delta-release-status {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.35rem;
}

.delta-release-status span {
  display: inline-flex;
  min-height: 20px;
  align-items: center;
  padding: 0.08rem 0.42rem;
  border: 1px solid var(--delta-mint-strong);
  border-radius: 3px;
  font-size: 0.68rem;
  font-weight: 750;
  line-height: 1.2;
}

.delta-release-alpha {
  background: var(--delta-mint);
  color: var(--delta-teal-dark);
}

.delta-release-experimental {
  border-color: #efd8a4 !important;
  background: var(--delta-amber-soft);
  color: #765600;
}

.delta-build {
  text-align: right;
}

.delta-build-status {
  color: var(--delta-teal);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
}

.delta-dot {
  width: 8px;
  height: 8px;
  display: inline-block;
  margin-right: 0.4rem;
  border-radius: 50%;
  background: var(--delta-teal);
}

.delta-eyebrow {
  color: var(--delta-teal);
  font-size: 0.72rem;
  font-weight: 750;
  text-transform: uppercase;
  margin: 0 0 0.35rem;
}

.delta-entry {
  position: relative;
  overflow: hidden;
  margin: 0 0 1rem;
  padding: 1.4rem 2rem 0.75rem;
  border-top: 1px solid var(--delta-mint-strong);
  border-bottom: 1px solid var(--delta-mint-strong);
  background: var(--delta-mint);
  color: var(--delta-ink);
}

.delta-entry-copy {
  position: relative;
  max-width: 760px;
}

.delta-entry-eyebrow {
  margin-bottom: 0.45rem;
  color: var(--delta-teal);
  font-size: 0.78rem;
  font-weight: 750;
  text-transform: uppercase;
}

.delta-entry h1 {
  max-width: 700px;
  margin: 0;
  color: #1a1a1a;
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 2.55rem !important;
  font-weight: 720;
  line-height: 1.08 !important;
}

.delta-entry-lede {
  max-width: 720px;
  margin: 0.75rem 0 0;
  color: var(--delta-ink);
  font-size: 1rem;
  line-height: 1.5;
}

.delta-entry-scope {
  max-width: 720px;
  margin: 0.35rem 0 0;
  color: var(--delta-muted);
  font-size: 0.86rem;
  line-height: 1.45;
}

.delta-style-trace {
  display: grid;
  grid-template-columns: minmax(180px, 0.55fr) minmax(0, 1.45fr);
  gap: 0.5rem 1.2rem;
  align-items: center;
  margin: 0.8rem 0 0;
  padding: 0.7rem 0;
  border-top: 1px solid var(--delta-mint-strong);
  border-bottom: 1px solid var(--delta-mint-strong);
}

.delta-style-trace figcaption {
  display: flex;
  grid-column: 1;
  grid-row: 1;
  min-width: 0;
  flex-direction: column;
  gap: 0.18rem;
  margin: 0;
}

.delta-trace-kicker {
  color: var(--delta-teal-dark);
  font-size: 0.68rem;
  font-weight: 800;
}

.delta-style-trace figcaption strong {
  color: var(--delta-ink);
  font-size: 0.92rem;
  line-height: 1.25;
}

.delta-style-trace figcaption > span:not(.delta-trace-kicker) {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.delta-style-trace figcaption small {
  color: var(--delta-tertiary);
  font-size: 0.66rem;
  line-height: 1.35;
}

.delta-trace-samples {
  display: grid;
  grid-column: 2;
  grid-row: 1;
  gap: 0.45rem;
  min-width: 0;
}

.delta-trace-row {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 0.55rem;
  align-items: end;
}

.delta-trace-row-label {
  color: var(--delta-muted);
  font-size: 0.66rem;
  font-weight: 750;
  text-transform: uppercase;
}

.delta-trace-tokens {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.28rem;
  min-width: 0;
}

.delta-trace-token {
  min-width: 0;
  padding: 0.15rem 0 0.2rem;
  border-bottom: 3px solid var(--delta-teal);
  color: var(--delta-ink);
  font-family: "SF Mono", "Cascadia Code", "Fira Code", monospace;
  font-size: 0.7rem;
  text-align: center;
}

.delta-trace-tone-1 {
  border-bottom-color: var(--delta-blue);
}

.delta-trace-tone-2 {
  border-bottom-color: var(--delta-amber);
}

.delta-trace-tone-3 {
  border-bottom-color: var(--delta-purple);
}

.delta-trace-key {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  gap: 0.7rem;
  align-items: center;
  grid-column: 1 / -1;
  grid-row: 2;
  min-width: 0;
}

.delta-trace-key > span {
  display: block;
  margin-bottom: 0;
  color: var(--delta-muted);
  font-size: 0.66rem;
  font-weight: 750;
  text-transform: uppercase;
}

.delta-trace-key ul {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.35rem 0.65rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.delta-trace-legend-item {
  display: grid;
  grid-template-columns: 9px minmax(0, 1fr);
  gap: 0.38rem;
  align-items: center;
  min-width: 0;
  color: var(--delta-ink);
  font-size: 0.7rem;
}

.delta-trace-legend-item > span {
  width: 9px;
  height: 9px;
  background: var(--delta-teal);
}

.delta-trace-legend-blue > span {
  background: var(--delta-blue);
}

.delta-trace-legend-amber > span {
  background: var(--delta-amber);
}

.delta-trace-legend-purple > span {
  background: var(--delta-purple);
}

.delta-method {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(150px, 0.55fr) minmax(0, 2fr);
  gap: 1rem;
  align-items: start;
  margin: 0.45rem 0 0;
  padding-top: 0.4rem;
  border-top: 1px solid var(--delta-soft-line);
}

.delta-method figcaption {
  display: flex;
  flex-direction: column;
  gap: 0.12rem;
  margin: 0;
}

.delta-method figcaption strong {
  color: var(--delta-ink);
  font-size: 0.82rem;
}

.delta-method figcaption span {
  color: var(--delta-muted);
  font-size: 0.7rem;
}

.delta-method ol {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.delta-method-step {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 0.5rem;
  min-width: 0;
  padding-top: 0.3rem;
  border-top: 3px solid var(--delta-teal);
}

.delta-method-number {
  color: var(--delta-teal-dark);
  font-size: 0.72rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.delta-method-step:nth-child(2) {
  border-top-color: var(--delta-blue);
}

.delta-method-step:nth-child(2) .delta-method-number {
  color: var(--delta-blue);
}

.delta-method-step:nth-child(3) {
  border-top-color: var(--delta-coral);
}

.delta-method-step:nth-child(3) .delta-method-number {
  color: var(--delta-coral);
}

.delta-method-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.15rem;
}

.delta-method-copy strong {
  color: var(--delta-ink);
  font-size: 0.8rem;
}

.delta-method-copy small {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.delta-purpose-guide {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr;
  margin: 0.45rem 0 0.55rem;
  border-top: 1px solid var(--delta-soft-line);
  border-bottom: 1px solid var(--delta-soft-line);
  background: var(--delta-paper);
}

.delta-purpose-guide-item {
  min-width: 0;
  padding: 0.6rem 0.8rem;
  border-right: 1px solid var(--delta-soft-line);
}

.delta-purpose-guide-item:last-child {
  border-right: 0;
}

.delta-purpose-guide-item span {
  display: block;
  margin-bottom: 0.2rem;
  color: var(--delta-muted);
  font-size: 0.72rem;
  font-weight: 750;
}

.delta-purpose-guide-item p {
  margin: 0;
  color: var(--delta-ink);
  font-size: 0.82rem;
  line-height: 1.32;
}

.delta-purpose-guide-question {
  border-top: 3px solid var(--delta-teal);
}

.delta-purpose-guide-use {
  border-top: 3px solid var(--delta-blue);
}

.delta-purpose-guide-boundary {
  border-top: 3px solid var(--delta-coral);
}

.delta-parameter-note {
  display: block;
  margin: 0 0 0.8rem;
  padding: 0;
  border-top: 1px solid var(--delta-line);
  border-bottom: 1px solid var(--delta-line);
  background: var(--delta-paper);
}

.delta-parameter-intro {
  display: grid;
  grid-template-columns: minmax(190px, 0.55fr) minmax(0, 1.45fr);
  gap: 1rem;
  padding: 0.85rem 0.95rem;
  border-left: 3px solid var(--delta-teal);
  border-bottom: 1px solid var(--delta-soft-line);
  background: var(--delta-family-canvas);
}

.delta-parameter-intro strong,
.delta-parameter-item strong {
  color: var(--delta-ink);
  font-size: 0.88rem;
}

.delta-parameter-intro p,
.delta-parameter-item p {
  margin: 0;
  color: var(--delta-muted);
  font-size: 0.86rem;
  line-height: 1.45;
}

.delta-parameter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
}

.delta-parameter-item {
  min-width: 0;
  padding: 0.75rem 0.85rem;
  border-top: 3px solid var(--delta-teal);
  background: var(--delta-mint);
}

.delta-parameter-item + .delta-parameter-item {
  border-left: 1px solid var(--delta-paper);
}

.delta-parameter-item:nth-child(2) {
  border-top-color: var(--delta-purple);
  background: var(--delta-purple-soft);
}

.delta-parameter-item:nth-child(3) {
  border-top-color: var(--delta-amber);
  background: var(--delta-amber-soft);
}

.delta-parameter-item strong {
  display: block;
  margin-bottom: 0.25rem;
  color: var(--delta-teal);
}

.delta-parameter-item:nth-child(2) strong {
  color: var(--delta-purple);
}

.delta-parameter-item:nth-child(3) strong {
  color: var(--delta-amber);
}

.delta-field-label {
  color: var(--delta-muted);
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 0.2rem;
}

.delta-purpose-question {
  color: var(--delta-ink);
  font-size: 1rem;
  font-weight: 650;
  line-height: 1.45;
  margin-bottom: 0.8rem;
}

.delta-detail-text {
  color: var(--delta-muted);
  font-size: 0.9rem;
  line-height: 1.5;
}

.delta-map {
  margin: 0.25rem 0 0.75rem;
  padding: 0.15rem 0.75rem;
  background: var(--delta-paper);
  border: 1px solid var(--delta-line);
  border-radius: 6px;
}

.delta-map-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0;
  padding: 0;
  list-style: none;
}

.delta-map-row {
  display: grid;
  grid-template-columns: 28px 1fr auto;
  gap: 0.65rem;
  align-items: center;
  min-height: 36px;
  padding: 0 0.75rem;
  border-right: 1px solid var(--delta-line);
}

.delta-map-row:last-child {
  border-right: 0;
}

.delta-map-number {
  color: var(--delta-muted);
  font-variant-numeric: tabular-nums;
}

.delta-map-name {
  color: var(--delta-ink);
  font-weight: 650;
}

.delta-map-state {
  color: var(--delta-muted);
  font-size: 0.72rem;
  text-transform: uppercase;
}

.delta-map-row.is-active .delta-map-number,
.delta-map-row.is-active .delta-map-state {
  color: var(--delta-teal);
  font-weight: 750;
}

[data-testid="stSidebar"] .delta-map-row.is-active .delta-map-number,
[data-testid="stSidebar"] .delta-map-row.is-active .delta-map-state {
  color: var(--delta-teal);
}

.delta-evidence-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.7rem;
  padding: 0.56rem 0;
  border-bottom: 1px solid var(--delta-line);
}

.delta-evidence-row:last-child {
  border-bottom: 0;
}

.delta-evidence-name {
  color: var(--delta-ink);
  font-size: 0.86rem;
  font-weight: 650;
}

.delta-evidence-state {
  color: var(--delta-muted);
  font-size: 0.76rem;
  text-align: right;
}

.delta-intake-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.8rem;
  align-items: center;
  min-height: 54px;
  padding: 0.55rem 0;
  border-bottom: 1px solid var(--delta-line);
}

.delta-intake-row:last-child {
  border-bottom: 0;
}

.delta-intake-identity {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.delta-intake-name {
  overflow-wrap: anywhere;
  color: var(--delta-ink);
  font-size: 0.88rem;
  font-weight: 700;
}

.delta-intake-role,
.delta-intake-metric {
  color: var(--delta-muted);
  font-size: 0.76rem;
}

.delta-archive-catalog {
  margin-top: 0.8rem;
  padding-top: 0.8rem;
  border-top: 1px solid var(--delta-line);
}

.delta-intake-metric {
  text-align: right;
}

.delta-timeline {
  margin: 0.4rem 0 1.25rem;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--delta-line);
}

.delta-timeline-row {
  display: grid;
  grid-template-columns: minmax(150px, 0.35fr) minmax(0, 1fr);
  gap: 1rem;
  padding: 0.7rem 0;
  border-bottom: 1px solid var(--delta-line);
}

.delta-timeline-date {
  color: var(--delta-teal);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.delta-timeline-work {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.1rem;
  color: var(--delta-ink);
}

.delta-timeline-work span {
  color: var(--delta-muted);
  font-size: 0.82rem;
}

div[class*="st-key-review_timeline_selector_"] [role="radiogroup"] {
  display: flex;
  flex-wrap: nowrap;
  gap: 0.5rem;
  max-width: 100%;
  padding: 0.35rem 0.2rem 0.65rem;
  overflow-x: auto;
}

div[class*="st-key-review_timeline_selector_"] [role="radio"] {
  flex: 0 0 min(220px, 72vw);
  min-height: 48px;
}

div[class*="st-key-review_timeline_selector_"] [role="radio"] p {
  line-height: 1.25;
  overflow-wrap: anywhere;
  white-space: normal;
}

.delta-timeline-detail {
  margin: 0.25rem 0 1rem;
  padding: 0.85rem 0;
  border-top: 1px solid var(--delta-line);
  border-bottom: 1px solid var(--delta-line);
}

.delta-timeline-detail h3 {
  margin: 0 0 0.65rem;
}

.delta-timeline-detail dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem 1rem;
  margin: 0;
}

.delta-timeline-detail dl div {
  min-width: 0;
}

.delta-timeline-detail dt {
  color: var(--delta-muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.delta-timeline-detail dd {
  margin: 0.1rem 0 0;
  color: var(--delta-ink);
  font-size: 0.86rem;
  overflow-wrap: anywhere;
}

.delta-composition-bars {
  display: grid;
  margin: 0.4rem 0 1rem;
  border-top: 1px solid var(--delta-line);
}

.delta-composition-row {
  display: grid;
  grid-template-columns: minmax(90px, 0.8fr) minmax(100px, 1fr) minmax(100px, 2fr) 56px;
  gap: 0.5rem;
  align-items: center;
  min-height: 46px;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--delta-line);
}

.delta-composition-dimension {
  color: var(--delta-muted);
  font-size: 0.76rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.delta-composition-label {
  min-width: 0;
  color: var(--delta-ink);
  font-size: 0.86rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.delta-bar-track {
  display: block;
  width: 100%;
  height: 12px;
  overflow: hidden;
  border: 1px solid var(--delta-line);
  border-radius: 3px;
  background: #edf2f0;
}

.delta-bar-fill {
  display: block;
  width: var(--delta-share);
  height: 100%;
  background: var(--delta-teal);
}

.delta-composition-count {
  color: var(--delta-ink);
  font-size: 0.82rem;
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}

.delta-table-scroll {
  max-width: 100%;
  margin-bottom: 1.25rem;
  overflow-x: auto;
}

.delta-table-scroll:focus,
.delta-table-scroll:focus-visible {
  outline: 3px solid var(--delta-focus);
  outline-offset: 2px;
}

.delta-review-table {
  width: 100%;
  min-width: 680px;
  border-collapse: collapse;
  background: var(--delta-paper);
}

.delta-review-table caption {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

.delta-review-table th,
.delta-review-table td {
  padding: 0.65rem;
  border: 1px solid var(--delta-line);
  color: var(--delta-ink);
  text-align: left;
  vertical-align: top;
}

.delta-review-table thead th {
  background: #edf2f0;
  font-size: 0.8rem;
}

.delta-composition-table {
  min-width: 600px;
}

.delta-timeline-table {
  min-width: 1100px;
}

.delta-parameter-table {
  min-width: 620px;
}

.delta-parameter-table tr[data-reference="true"] th,
.delta-parameter-table tr[data-reference="true"] td {
  background: #edf7f2;
  font-weight: 650;
}

.delta-result-cell-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.5rem;
  margin: 0.7rem 0 0.8rem;
}

.delta-result-cell {
  display: flex;
  min-width: 0;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.28rem;
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--delta-mint-strong);
  border-radius: 6px;
  background: var(--delta-mint-soft);
  color: var(--delta-teal-dark);
}

.delta-result-cell-not_enough_features {
  border-color: var(--delta-amber);
  background: var(--delta-amber-soft);
  color: var(--delta-amber-text);
}

.delta-result-cell-failed {
  border-color: var(--delta-coral);
  background: var(--delta-coral-soft);
  color: var(--delta-coral-text);
}

.delta-result-cell-icon {
  flex: 0 0 auto;
  font-size: 0.82rem;
  font-weight: 800;
}

.delta-result-cell-mfw {
  color: currentColor;
  font-size: 0.74rem;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}

.delta-result-cell-divider {
  color: currentColor;
  font-size: 0.78rem;
}

.delta-result-cell strong {
  color: currentColor;
  font-size: 0.76rem;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.delta-result-status-table,
.delta-result-matrix,
.delta-neighbour-table,
.delta-mds-table {
  min-width: 560px;
  font-variant-numeric: tabular-nums;
}

.delta-result-status-table tr[data-status="complete"] th {
  box-shadow: inset 4px 0 0 var(--delta-teal);
}

.delta-result-status-table tr[data-status="not_enough_features"] th {
  box-shadow: inset 4px 0 0 var(--delta-amber);
}

.delta-result-status-table tr[data-status="failed"] th {
  box-shadow: inset 4px 0 0 var(--delta-coral);
}

.st-key-p009_mds_square [data-testid="stVegaLiteChart"] {
  width: 100% !important;
  max-width: 100%;
  height: auto !important;
  aspect-ratio: 60 / 61;
}

.st-key-p009_mds_square [data-testid="stVegaLiteChart"] > div,
.st-key-p009_mds_square [data-testid="stVegaLiteChart"] svg {
  width: 100% !important;
  max-width: 100% !important;
  height: auto !important;
}

@media (min-width: 761px) and (max-width: 1320px) {
  .st-key-p009_mds_square [data-testid="stVegaLiteChart"] {
    aspect-ratio: 60 / 61.3;
  }
}

@media (max-width: 340px) {
  .st-key-p009_mds_square [data-testid="stVegaLiteChart"] {
    aspect-ratio: 60 / 61.18;
  }
}

.delta-result-matrix th,
.delta-result-matrix td,
.delta-mds-table td,
.delta-neighbour-table td {
  white-space: nowrap;
}

.delta-result-boundary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0.5rem 0 1.6rem;
  border-top: 1px solid var(--delta-line);
  border-bottom: 1px solid var(--delta-line);
  background: var(--delta-family-canvas);
}

.delta-result-boundary > div {
  min-width: 0;
  padding: 0.85rem 1rem;
}

.delta-result-boundary > div + div {
  border-left: 3px solid var(--delta-coral);
  background: var(--delta-coral-soft);
}

.delta-result-boundary strong {
  display: block;
  margin-bottom: 0.25rem;
  color: var(--delta-ink);
  font-size: 0.84rem;
}

.delta-result-boundary p {
  margin: 0;
  color: var(--delta-muted);
  font-size: 0.8rem;
  line-height: 1.48;
}

.delta-evidence-bars {
  display: grid;
  gap: 0.8rem;
  margin: 0.85rem 0 1.1rem;
}

.delta-evidence-bar-row {
  display: grid;
  grid-template-columns: minmax(9rem, 1.1fr) minmax(16rem, 3fr);
  gap: 0.75rem;
  align-items: start;
}

.delta-evidence-bar-label {
  color: var(--delta-ink);
  font-size: 0.84rem;
  font-weight: 650;
  overflow-wrap: anywhere;
}

.delta-evidence-bar-series {
  display: grid;
  gap: 0.35rem;
}

.delta-evidence-bar-item {
  display: grid;
  grid-template-columns: minmax(7rem, 1fr) minmax(8rem, 2fr) 4.5rem;
  gap: 0.5rem;
  align-items: center;
  color: var(--delta-muted);
  font-size: 0.76rem;
}

.delta-evidence-bar-track {
  display: block;
  width: 100%;
  height: 0.55rem;
  overflow: hidden;
  border: 1px solid var(--delta-line);
  border-radius: 3px;
  background: #edf2f0;
}

.delta-evidence-bar-fill {
  display: block;
  width: var(--delta-share);
  height: 100%;
  background: var(--delta-teal);
}

.delta-evidence-bar-item[data-series="1"] .delta-evidence-bar-fill {
  background: #c5842f;
}

.delta-evidence-bar-item[data-series="2"] .delta-evidence-bar-fill {
  background: #5e6f86;
}

.delta-evidence-bar-value {
  color: var(--delta-ink);
  font-variant-numeric: tabular-nums;
  text-align: right;
}

@media (max-width: 720px) {
  .delta-evidence-bar-row {
    grid-template-columns: 1fr;
    gap: 0.35rem;
  }

  .delta-evidence-bar-item {
    grid-template-columns: minmax(6rem, 1fr) minmax(7rem, 2fr) 3.5rem;
  }
}

.delta-timeline-table tr[aria-current="true"] th,
.delta-timeline-table tr[aria-current="true"] td {
  background: #edf7f2;
}

.delta-completeness-table {
  min-width: 1540px;
}

.delta-completeness-table th[scope="row"] {
  min-width: 180px;
}

.delta-completeness-cell {
  min-width: 180px;
  border-top-width: 4px !important;
}

.delta-completeness-cell strong,
.delta-completeness-cell span,
.delta-completeness-cell small {
  display: block;
  overflow-wrap: anywhere;
}

.delta-completeness-cell span {
  margin-top: 0.25rem;
  color: var(--delta-ink);
  font-size: 0.78rem;
}

.delta-completeness-cell small {
  margin-top: 0.35rem;
  color: var(--delta-muted);
  font-size: 0.7rem;
}

.delta-status-complete {
  border-top-color: #287a50 !important;
  background: #edf7f2;
}

.delta-status-missing {
  border-top-color: #b42318 !important;
  background: #fdf0ef;
}

.delta-status-warning {
  border-top-color: #8a5a00 !important;
  background: #fff5e6;
}

.delta-status-conflict {
  border-top-color: #7a284f !important;
  background: #faeef4;
}

.delta-issues {
  display: grid;
  gap: 0.65rem;
  margin: 0.4rem 0 1.25rem;
  padding: 0;
  list-style: none;
}

.delta-issue {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.75rem;
  background: var(--delta-paper);
  border: 1px solid var(--delta-line);
  border-left-width: 5px;
  border-radius: 5px;
  color: var(--delta-ink);
}

.delta-issue-blocker {
  border-left-color: #b42318;
}

.delta-issue-warning {
  border-left-color: #8a5a00;
}

.delta-issue-information {
  border-left-color: var(--delta-focus);
}

.delta-issue-code {
  color: var(--delta-muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.delta-issue span {
  color: var(--delta-muted);
  font-size: 0.86rem;
}

.st-key-corpus_stage,
.st-key-describe_stage,
.st-key-run_state {
  background: var(--delta-paper);
  border-radius: 6px;
}

[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--delta-line);
  border-radius: 6px;
  box-shadow: none;
}

[data-testid="stButton"] button,
[data-testid="stFileUploaderDropzone"] {
  border-radius: 5px;
}

[data-testid="stButton"] button {
  min-height: 3rem;
  white-space: normal;
}

.st-key-boundary_panel {
  padding-left: 1rem;
  border-left: 3px solid var(--delta-coral);
  background: transparent;
}

[data-testid="stFileUploaderDropzone"] {
  min-height: 112px;
}

[data-testid="stSegmentedControl"] button {
  min-height: 44px;
}

[role="radiogroup"] button[role="radio"] {
  min-height: 44px;
}

button[aria-label^="Help for"] {
  min-width: 24px;
  min-height: 24px;
}

button:focus-visible,
a[href]:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible,
[role="radio"]:focus-visible,
[role="combobox"]:focus-visible,
summary:focus-visible,
[tabindex]:not([tabindex="-1"]):focus-visible {
  outline: 3px solid var(--delta-focus) !important;
  outline-offset: 2px;
}

h1,
h2,
h3,
p,
span,
label,
button {
  letter-spacing: 0;
}

div[data-testid="stMainBlockContainer"] h1 {
  font-size: 2rem;
  line-height: 1.18;
  letter-spacing: 0 !important;
}

div[data-testid="stMainBlockContainer"] h2 {
  font-size: 1.25rem;
  line-height: 1.25;
  letter-spacing: 0 !important;
}

div[data-testid="stMainBlockContainer"] h3 {
  font-size: 1rem;
  line-height: 1.3;
  letter-spacing: 0 !important;
}

@media (max-width: 760px) {
  .delta-result-cell-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .delta-result-boundary {
    grid-template-columns: 1fr;
  }

  .delta-result-boundary > div + div {
    border-top: 1px solid var(--delta-line);
    border-left-width: 3px;
  }

  [data-testid="stMainBlockContainer"] {
    padding-left: 1rem;
    padding-right: 1rem;
    padding-top: 0.75rem;
  }

  [data-testid="stSidebar"],
  [data-testid="stSidebarCollapsedControl"] {
    display: none !important;
  }

  .delta-header {
    align-items: flex-start;
    min-height: 64px;
    margin-bottom: 0.5rem;
    padding-bottom: 0.7rem;
  }

  .delta-entry {
    min-height: 0;
    padding: 1.25rem 1rem 0.9rem;
  }

  .delta-entry h1 {
    max-width: 100%;
    font-size: 2rem !important;
    line-height: 1.12 !important;
  }

  .delta-entry-lede {
    font-size: 0.92rem;
    line-height: 1.42;
  }

  .delta-entry-scope {
    font-size: 0.8rem;
  }

  .delta-style-trace {
    gap: 0.45rem 0.9rem;
    margin-top: 0.65rem;
    padding: 0.6rem 0;
  }

  .delta-trace-row {
    grid-template-columns: 72px minmax(0, 1fr);
    gap: 0.35rem;
  }

  .delta-trace-row-label,
  .delta-trace-token,
  .delta-trace-key > span,
  .delta-trace-legend-item {
    font-size: 0.62rem;
  }

  .delta-trace-key ul {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.35rem;
  }

  .delta-purpose-guide {
    grid-template-columns: 1fr;
  }

  .delta-purpose-guide-item {
    padding: 0.65rem 0.75rem;
    border-right: 0;
    border-bottom: 1px solid var(--delta-soft-line);
  }

  .delta-purpose-guide-item:last-child {
    border-bottom: 0;
  }

  .delta-parameter-intro,
  .delta-parameter-grid {
    grid-template-columns: 1fr;
  }

  .delta-parameter-intro {
    gap: 0.3rem;
  }

  .delta-parameter-item,
  .delta-parameter-item + .delta-parameter-item {
    padding: 0.7rem 0.75rem;
    border-left: 0;
  }

  .delta-parameter-item + .delta-parameter-item {
    margin-top: 0;
    border-top-width: 3px;
  }

  .delta-build {
    max-width: 44%;
  }

  .delta-build-meta {
    display: none;
  }

  .delta-mark {
    width: 38px;
    height: 38px;
    font-size: 1.3rem;
  }

  div[data-testid="stMainBlockContainer"] h1 {
    font-size: 1.75rem;
    line-height: 1.22;
  }

  div[data-testid="stMainBlockContainer"] h2 {
    font-size: 1.25rem;
  }

  .delta-map {
    margin-bottom: 0.5rem;
    padding: 0.25rem 0.65rem;
  }

  .delta-map-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .delta-map-row {
    grid-template-columns: 24px 1fr auto;
    min-height: 38px;
    padding: 0;
    border-bottom: 1px solid var(--delta-line);
  }

  .delta-map-row:nth-child(odd) {
    padding-right: 0.5rem;
    border-right: 1px solid var(--delta-line);
  }

  .delta-map-row:nth-child(even) {
    padding-left: 0.5rem;
    border-right: 0;
  }

  .delta-map-row:nth-last-child(-n + 2) {
    border-bottom: 0;
  }

  .st-key-research_purpose [role="radiogroup"] {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    flex-wrap: initial !important;
  }

  .st-key-research_purpose button[role="radio"] {
    flex: initial !important;
    min-width: 0 !important;
    min-height: 48px;
    height: auto;
    padding-right: 0.35rem;
    padding-left: 0.35rem;
    font-size: 0.875rem;
  }

  .st-key-research_purpose button[role="radio"]:last-child {
    grid-column: 1 / -1;
  }

  .st-key-research_purpose button[role="radio"] p {
    overflow: visible;
    line-height: 1.1;
    white-space: normal;
    text-overflow: clip;
  }

  .delta-intake-row {
    grid-template-columns: 1fr;
    gap: 0.25rem;
  }

  .delta-intake-metric {
    text-align: left;
  }

  .delta-timeline-row {
    grid-template-columns: 1fr;
    gap: 0.2rem;
  }

  .delta-timeline-detail dl {
    grid-template-columns: 1fr;
  }

  .delta-composition-row {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.25rem 0.75rem;
    padding: 0.65rem 0;
  }

  .delta-composition-dimension,
  .delta-composition-label {
    grid-column: 1;
  }

  .delta-composition-count {
    grid-column: 2;
    grid-row: 1 / span 2;
    align-self: center;
  }

  .delta-bar-track {
    grid-column: 1 / -1;
  }
}

@media (max-width: 480px) {
  .delta-entry {
    padding: 1.1rem 1rem 0.75rem;
  }

  .delta-entry-eyebrow {
    margin-bottom: 0.3rem;
    font-size: 0.7rem;
  }

  .delta-entry-lede {
    margin-top: 0.55rem;
  }

  .delta-entry-scope {
    margin-top: 0.25rem;
  }

  .delta-style-trace {
    grid-template-columns: 1fr;
    gap: 0.4rem;
    margin-top: 0.6rem;
    padding: 0.55rem 0;
  }

  .delta-style-trace figcaption {
    grid-column: 1;
    grid-row: auto;
    gap: 0.12rem;
  }

  .delta-trace-samples,
  .delta-trace-key {
    grid-column: 1;
    grid-row: auto;
  }

  .delta-style-trace figcaption > span:not(.delta-trace-kicker) {
    display: none;
  }

  .delta-trace-row:nth-child(n + 2) {
    display: none;
  }

  .delta-trace-key {
    grid-template-columns: 1fr;
    gap: 0.25rem;
  }

  .delta-trace-key ul {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.25rem 0.6rem;
  }

  .delta-method {
    grid-template-columns: 1fr;
    gap: 0.35rem;
    margin-top: 0.5rem;
    padding-top: 0.45rem;
  }

  .delta-method figcaption {
    flex-flow: row wrap;
    gap: 0.35rem;
  }

  .delta-method ol {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.35rem;
  }

  .delta-method-step {
    grid-template-columns: 18px minmax(0, 1fr);
    gap: 0.25rem;
    padding-top: 0.25rem;
  }

  .delta-method-copy {
    display: block;
  }

  .delta-method-copy small {
    display: none;
  }
}

@media (max-width: 370px) {
  .delta-header {
    min-height: 54px;
    padding-bottom: 0.45rem;
  }

  .delta-brand-subtitle {
    display: none;
  }

  .delta-release-status {
    gap: 0.2rem;
    margin-top: 0.25rem;
  }

  .delta-release-status span {
    padding-right: 0.3rem;
    padding-left: 0.3rem;
    font-size: 0.62rem;
  }

  .delta-build {
    max-width: none;
  }

  .delta-build-status {
    font-size: 0.68rem;
    white-space: nowrap;
  }

  .delta-entry {
    padding-top: 0.9rem;
    padding-bottom: 0.55rem;
  }

  .delta-entry h1 {
    font-size: 1.875rem !important;
  }

  .delta-entry-lede {
    font-size: 0.875rem;
    line-height: 1.36;
  }

  .delta-entry-scope {
    font-size: 0.76rem;
    line-height: 1.34;
  }

  .delta-style-trace figcaption small,
  .delta-method figcaption span {
    display: none;
  }

  .delta-trace-key ul {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.2rem 0.5rem;
  }

  .delta-trace-legend-item {
    grid-template-columns: 7px minmax(0, 1fr);
    gap: 0.2rem;
    font-size: 0.56rem;
    line-height: 1.2;
  }

  .delta-trace-legend-item > span {
    width: 7px;
    height: 7px;
  }

  .delta-method {
    margin-top: 0.35rem;
    padding-top: 0.3rem;
  }

  .delta-method figcaption strong,
  .delta-method-copy strong {
    font-size: 0.7rem;
  }

  .delta-method-step {
    padding-top: 0.15rem;
    border-top-width: 2px;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}

@media (max-width: 340px) {
  [data-testid="stMainBlockContainer"] {
    padding-top: 0.375rem;
  }

  .delta-entry {
    margin-bottom: 0.65rem;
    padding: 0.8rem 0.9rem 0.65rem;
  }

  .delta-entry h1 {
    font-size: 1.75rem !important;
    line-height: 1.08 !important;
  }

  .delta-entry-lede {
    font-size: 0.875rem;
    line-height: 1.4;
  }

  .delta-entry-scope {
    font-size: 0.72rem;
    line-height: 1.3;
  }

  .delta-trace-row {
    grid-template-columns: 64px minmax(0, 1fr);
  }

  .delta-method {
    margin-top: 0.25rem;
  }

  .delta-method-step {
    display: block;
    text-align: center;
  }

  .delta-method-number {
    display: block;
    margin-bottom: 0.1rem;
  }

  .delta-method-copy strong {
    font-size: 0.62rem;
  }

  .delta-map {
    margin-bottom: 0.25rem;
  }

  .delta-map-state {
    display: none;
  }

  .delta-map-row {
    grid-template-columns: 24px minmax(0, 1fr);
  }
}

/* Phase B: A5.1 interaction and accessibility contract. */
.delta-skip-link {
  position: fixed;
  top: 0;
  left: -9999px;
  z-index: 1000000;
  min-height: 44px;
  padding: 10px 18px;
  border-radius: 0 0 6px 0;
  background: var(--delta-teal);
  color: #ffffff;
  font-weight: 700;
}

.delta-skip-link:focus {
  left: 0;
}

.delta-main-anchor {
  display: block;
  width: 1px;
  height: 1px;
  scroll-margin-top: 12px;
}

.delta-header {
  min-height: 64px;
  padding: 12px 0;
  margin-bottom: 16px;
}

.delta-mark {
  width: 40px;
  height: 40px;
  font-size: 22px;
}

.delta-release-status span {
  min-height: 20px;
  padding: 1px 10px;
  border-radius: 999px;
  font-size: 12px;
}

.delta-brand-subtitle,
.delta-build-meta,
.delta-build-status,
.delta-eyebrow,
.delta-entry-eyebrow,
.delta-map-number,
.delta-map-state {
  font-size: 12px;
}

.delta-entry {
  overflow: visible;
  margin: 0;
  padding: 16px 0 4px;
  border: 0;
  background: transparent;
}

.delta-entry h1 {
  max-width: 760px;
  font-size: 34px !important;
  font-weight: 700;
  line-height: 1.15 !important;
}

.delta-entry-lede {
  margin-top: 8px;
  font-size: 16px;
  line-height: 1.5;
}

.delta-entry-scope {
  margin-top: 4px;
  font-size: 13px;
}

.delta-stylometry-orientation {
  margin-top: 32px;
}

.delta-stylometry-orientation > h2 {
  margin: 0;
}

.delta-orientation-caption {
  margin: 4px 0 10px;
  color: var(--delta-muted);
  font-size: 13px;
}

.delta-method {
  display: block;
  margin: 0;
  padding: 0;
  border: 0;
}

.delta-method ol {
  gap: 10px;
}

.delta-method-step {
  min-height: 74px;
  padding: 10px 12px;
  border: 1px solid var(--delta-line);
  border-top: 3px solid var(--delta-teal);
  border-radius: 6px;
  background: var(--delta-paper);
}

.delta-method-number,
.delta-method-copy strong,
.delta-method-copy small,
.delta-trace-kicker,
.delta-style-trace figcaption small,
.delta-trace-row-label,
.delta-trace-token,
.delta-trace-key > span,
.delta-trace-legend-item {
  font-size: 12px;
}

.delta-method-copy small {
  position: static;
  width: auto;
  height: auto;
  overflow: visible;
  clip-path: none;
  white-space: normal;
  color: var(--delta-muted);
  line-height: 1.4;
}

.delta-style-trace {
  margin-top: 14px;
  padding: 14px 16px;
  border: 1px solid var(--delta-line);
  border-radius: 6px;
  background: var(--delta-paper);
}

.delta-map {
  min-height: 46px;
  margin: 16px 0 20px;
  padding: 0;
}

.delta-map-row {
  min-height: 46px;
  border-top: 3px solid transparent;
}

.delta-map-row.is-active {
  border-top-color: var(--delta-teal);
}

.delta-context-strip {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 16px;
  padding: 10px 14px;
  border: 1px solid var(--delta-line);
  border-left: 3px solid var(--delta-teal);
  border-radius: 6px;
  background: var(--delta-paper);
}

.delta-context-strip span {
  flex: 0 0 auto;
  color: var(--delta-teal-dark);
  font-size: 13px;
  font-weight: 750;
}

.delta-context-strip p {
  margin: 0;
  color: var(--delta-muted);
  font-size: 13px;
}

.delta-readiness-band {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: 12px;
  margin: 12px 0 16px;
  padding: 14px 16px;
  border: 1px solid #a9d8c6;
  border-left: 4px solid var(--delta-teal);
  border-radius: 6px;
  background: var(--delta-mint-soft);
}

.delta-readiness-icon {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--delta-teal);
  color: #ffffff;
  font-weight: 800;
}

.delta-readiness-band.is-exploratory {
  border-color: #d7bd76;
  border-left-color: var(--delta-amber-text);
  background: var(--delta-amber-soft);
}

.delta-readiness-band.is-exploratory .delta-readiness-icon {
  background: var(--delta-amber-text);
}

.delta-readiness-band.is-exploratory .delta-readiness-copy strong,
.delta-readiness-band.is-exploratory .delta-readiness-counts {
  color: var(--delta-amber-text);
}

.delta-readiness-copy strong {
  display: block;
  color: var(--delta-teal-dark);
  font-size: 14px;
}

.delta-readiness-copy p {
  margin: 4px 0 0;
  color: var(--delta-muted);
  font-size: 13px;
  line-height: 1.45;
}

.delta-readiness-counts {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px 12px;
  color: var(--delta-teal-dark);
  font-size: 12px;
  font-weight: 750;
  white-space: nowrap;
}

.delta-analysis-status {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: start;
  gap: 12px;
  margin: 12px 0;
  padding: 14px 16px;
  border: 1px solid #a9d8c6;
  border-left: 4px solid var(--delta-teal);
  border-radius: 6px;
  background: var(--delta-mint-soft);
}

.delta-analysis-status.is-alert {
  border-color: #e6a99c;
  border-left-color: var(--delta-coral-text);
  background: #fff5f1;
}

.delta-analysis-status-icon {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--delta-teal);
  color: #ffffff;
  font-size: 13px;
  font-weight: 800;
}

.delta-analysis-status.is-alert .delta-analysis-status-icon {
  background: var(--delta-coral-text);
}

.delta-analysis-status-copy strong {
  display: block;
  color: var(--delta-teal-dark);
  font-size: 14px;
}

.delta-analysis-status.is-alert .delta-analysis-status-copy strong {
  color: var(--delta-coral-text);
}

.delta-analysis-status-copy p,
.delta-analysis-reference {
  display: block;
  margin: 4px 0 0;
  color: var(--delta-muted);
  font-size: 13px;
  line-height: 1.45;
}

.delta-review-metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin: 0 0 22px;
}

.delta-review-metric {
  display: flex;
  min-width: 0;
  min-height: 98px;
  flex-direction: column;
  padding: 12px;
  border: 1px solid var(--delta-line);
  border-top: 3px solid var(--delta-teal);
  border-radius: 6px;
  background: var(--delta-paper);
}

.delta-review-metric.is-warning {
  border-top-color: var(--delta-amber-text);
  background: #fffaf0;
}

.delta-review-metric.is-blocked {
  border-top-color: var(--delta-coral-text);
  background: #fff5f1;
}

.delta-review-metric span,
.delta-review-metric small {
  color: var(--delta-muted);
  font-size: 12px;
  line-height: 1.35;
}

.delta-review-metric strong {
  margin: 4px 0;
  color: var(--delta-ink);
  font-family: var(--delta-heading-font);
  font-size: 26px;
  line-height: 1;
}

.delta-purpose-guide {
  border: 1px solid var(--delta-line);
  border-radius: 6px;
}

.delta-purpose-guide-desktop {
  display: block;
}

.delta-purpose-guide-mobile {
  display: none;
}

.delta-purpose-guide-item span,
.delta-purpose-guide-item p,
.delta-field-label,
.delta-detail-text,
.delta-evidence-name,
.delta-evidence-state,
.delta-intake-role,
.delta-intake-metric,
.delta-timeline-work span,
.delta-timeline-detail dt,
.delta-timeline-detail dd,
.delta-composition-dimension,
.delta-composition-count,
.delta-result-cell-mfw,
.delta-result-cell small,
.delta-result-boundary strong,
.delta-result-boundary p,
.delta-evidence-bar-label,
.delta-evidence-bar-item,
.delta-completeness-cell span,
.delta-completeness-cell small,
.delta-issue span {
  font-size: 12px;
}

.st-key-research_purpose,
.st-key-corpus_input_mode,
.st-key-p009_result_cell_selector,
.st-key-research_purpose [data-testid="stRadio"],
.st-key-corpus_input_mode [data-testid="stRadio"],
.st-key-p009_result_cell_selector [data-testid="stRadio"] {
  width: 100%;
}

.st-key-research_purpose [data-testid="stRadioGroup"],
.st-key-corpus_input_mode [data-testid="stRadioGroup"],
.st-key-p009_result_cell_selector [data-testid="stRadioGroup"] {
  display: grid !important;
  gap: 10px;
  width: 100%;
}

.st-key-research_purpose [data-testid="stRadioGroup"] {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.st-key-corpus_input_mode [data-testid="stRadioGroup"] {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.st-key-p009_result_cell_selector [data-testid="stRadioGroup"] {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.st-key-research_purpose label[data-testid="stRadioOption"],
.st-key-corpus_input_mode label[data-testid="stRadioOption"],
.st-key-p009_result_cell_selector label[data-testid="stRadioOption"] {
  display: flex;
  align-items: center;
  min-width: 0;
  min-height: 44px;
  padding: 8px 12px;
  border: 1px solid var(--delta-control-line);
  border-radius: 6px;
  background: var(--delta-paper);
}

.st-key-research_purpose label[data-testid="stRadioOption"]:has(input:checked),
.st-key-corpus_input_mode label[data-testid="stRadioOption"]:has(input:checked),
.st-key-p009_result_cell_selector label[data-testid="stRadioOption"]:has(input:checked) {
  border-color: var(--delta-teal);
  background: var(--delta-mint-soft);
  box-shadow: inset 0 -3px 0 var(--delta-teal);
}

.st-key-research_purpose label[data-testid="stRadioOption"]:has(input:focus-visible),
.st-key-corpus_input_mode label[data-testid="stRadioOption"]:has(input:focus-visible),
.st-key-p009_result_cell_selector label[data-testid="stRadioOption"]:has(input:focus-visible) {
  outline: 3px solid rgba(15, 110, 86, 0.28);
  outline-offset: 2px;
}

.st-key-persisted_upload_choices {
  display: none !important;
}

[data-testid="stFileUploaderDropzone"] {
  min-height: 120px;
  border: 2px dashed var(--delta-teal);
  border-radius: 8px;
  background: var(--delta-mint-soft);
}

[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button,
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stCheckbox"] label,
[data-testid="stExpander"] summary,
.delta-tech summary,
[data-testid="stVegaLiteChart"] details > summary,
button[aria-label^="Help for"],
button[data-testid="stBaseButton-elementToolbar"] {
  min-width: 44px;
  min-height: 44px;
}

[data-testid="stVegaLiteChart"] details > summary {
  display: flex;
  align-items: center;
  justify-content: center;
}

[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] [role="combobox"],
[data-testid="stSelectbox"] button {
  min-height: 44px;
}

[data-testid="stSelectbox"] button {
  min-width: 44px;
}

[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button,
[data-testid="stFileUploaderDropzone"] button {
  border-color: var(--delta-control-line);
  border-radius: 4px;
}

.delta-scroll-note {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0 6px;
  color: var(--delta-muted);
  font-size: 13px;
  line-height: 1.4;
}

.delta-table-scroll {
  border: 1px solid var(--delta-line);
  border-radius: 6px;
  background: var(--delta-paper);
  scrollbar-color: var(--delta-control-line) var(--delta-soft-line);
  scrollbar-width: thin;
}

.delta-review-table thead th {
  background: var(--delta-sidebar);
  color: var(--delta-muted);
  font-size: 12px;
  text-transform: uppercase;
}

.delta-method-key {
  padding: 14px 16px;
  border: 1px solid var(--delta-line);
  border-radius: 8px;
  background: var(--delta-paper);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.delta-method-key h3 {
  margin: 0 0 8px;
  font-size: 14px;
}

.delta-method-key dl {
  display: grid;
  gap: 8px;
  margin: 0;
}

.delta-method-key dt {
  color: var(--delta-teal-dark);
  font-size: 13px;
  font-weight: 750;
}

.delta-method-key dd,
.delta-method-key p {
  margin: 0;
  color: var(--delta-muted);
  font-size: 13px;
  line-height: 1.45;
}

.delta-mds-legend {
  display: grid;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--delta-line);
  color: var(--delta-ink);
  font-size: 13px;
}

.delta-mds-legend span {
  display: flex;
  align-items: center;
  gap: 8px;
}

.delta-mds-legend i {
  display: inline-block;
  width: 12px;
  height: 12px;
  flex: 0 0 12px;
  background: var(--delta-teal);
}

.delta-mds-known {
  border-radius: 50%;
}

.delta-mds-unknown {
  background: var(--delta-coral) !important;
  transform: rotate(45deg);
}

.delta-issue {
  padding: 12px 16px;
  border-radius: 6px;
}

.delta-issue-heading {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.delta-issue-count {
  padding: 1px 9px;
  border: 1px solid #efd8a4;
  border-radius: 999px;
  background: var(--delta-amber-soft);
  color: var(--delta-amber-text) !important;
  font-size: 12px !important;
  font-weight: 750;
}

.delta-issue-severity {
  color: var(--delta-amber-text) !important;
  font-size: 12px !important;
  font-weight: 750;
  text-transform: uppercase;
}

.delta-tech {
  margin-top: 8px;
  border: 1px solid var(--delta-line);
  border-radius: 4px;
  background: var(--delta-canvas);
}

.delta-tech summary {
  display: flex;
  align-items: center;
  padding: 4px 12px;
  color: var(--delta-muted);
  cursor: pointer;
  font-size: 13px;
  font-weight: 650;
  list-style: none;
}

.delta-tech summary::after {
  content: "\\25B8";
  margin-left: auto;
  color: var(--delta-tertiary);
}

.delta-tech[open] summary::after {
  content: "\\25BE";
}

.delta-tech-body {
  padding: 4px 12px 10px;
  color: var(--delta-muted);
  font-size: 13px;
  overflow-wrap: anywhere;
}

.delta-tech-body ul {
  margin: 0;
  padding-left: 18px;
}

.delta-tech code {
  padding: 0 4px;
  border: 1px solid var(--delta-line);
  border-radius: 3px;
  background: var(--delta-paper);
  font-size: 12px;
}

.delta-footer {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
  margin-top: 32px;
  padding-top: 16px;
  border-top: 1px solid var(--delta-line);
}

.delta-footer p {
  margin: 0;
  color: var(--delta-muted);
  font-size: 13px;
  line-height: 1.45;
}

div[data-testid="stMainBlockContainer"] h1 {
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
}

div[data-testid="stMainBlockContainer"] h2 {
  font-size: 19px;
  font-weight: 650;
}

div[data-testid="stMainBlockContainer"] h3 {
  font-size: 16px;
  font-weight: 650;
}

@media (max-width: 760px) {
  [data-testid="stMainBlockContainer"] {
    padding-right: 14px;
    padding-left: 14px;
  }

  .delta-brand-subtitle,
  .delta-entry-scope {
    display: none;
  }

  .delta-entry {
    padding: 4px 0 0;
  }

  .delta-entry h1 {
    font-size: 26px !important;
    padding: 0;
  }

  .delta-entry-lede {
    margin-top: 4px;
    font-size: 14px !important;
    line-height: 1.4;
  }

  .st-key-research_purpose [data-testid="stRadioGroup"] {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
  }

  .st-key-research_purpose label[data-testid="stRadioOption"]:last-child {
    grid-column: 1 / -1;
  }

  .st-key-research_purpose [data-testid="stCaptionContainer"] {
    position: absolute !important;
    width: 1px !important;
    height: 1px !important;
    padding: 0 !important;
    margin: -1px !important;
    overflow: hidden !important;
    clip: rect(0, 0, 0, 0) !important;
    white-space: nowrap !important;
    border: 0 !important;
  }

  .delta-header {
    min-height: 56px;
    padding: 8px 0;
    margin-bottom: 6px;
  }

  .st-key-p009_result_cell_selector [data-testid="stRadioGroup"] {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .delta-purpose-guide-desktop {
    display: none;
  }

  .delta-purpose-guide-mobile {
    display: block;
    margin-top: 14px;
    border: 1px solid var(--delta-line);
    border-radius: 6px;
    background: var(--delta-paper);
  }

  .delta-purpose-guide-mobile summary {
    display: flex;
    align-items: center;
    min-height: 44px;
    padding: 4px 14px;
    color: var(--delta-ink);
    font-size: 14px;
    font-weight: 650;
    cursor: pointer;
    list-style: none;
  }

  .delta-purpose-guide-mobile summary::-webkit-details-marker {
    display: none;
  }

  .delta-purpose-guide-mobile summary::after {
    content: "▸";
    margin-left: auto;
    color: var(--delta-tertiary);
  }

  .delta-purpose-guide-mobile[open] summary::after {
    content: "▾";
  }

  .delta-purpose-guide-mobile summary:focus-visible {
    outline: 3px solid rgba(15, 110, 86, 0.28);
    outline-offset: 2px;
  }

  .delta-purpose-guide-mobile .delta-purpose-guide {
    margin: 0;
    border: 0;
    border-top: 1px solid var(--delta-line);
    border-radius: 0;
  }

  .delta-map {
    margin-top: 8px;
    margin-bottom: 12px;
  }

  .delta-map-upload {
    display: none;
  }

  .st-key-corpus_stage {
    gap: 8px;
    padding: 14px;
  }

  .st-key-corpus_stage > :first-child {
    display: none;
  }

  .st-key-corpus_stage > [data-testid="stLayoutWrapper"]:nth-child(2) {
    display: block;
  }

  .st-key-corpus_stage > [data-testid="stLayoutWrapper"]:nth-child(2)
    [data-testid="stHorizontalBlock"] {
    display: block;
  }

  .st-key-corpus_stage > [data-testid="stLayoutWrapper"]:nth-child(2)
    [data-testid="stColumn"]:first-child {
    width: 100% !important;
  }

  .st-key-corpus_stage > [data-testid="stLayoutWrapper"]:nth-child(2)
    [data-testid="stColumn"]:last-child {
    display: none;
  }

  .st-key-corpus_inputs {
    gap: 8px;
  }

  .delta-map-list {
    display: block;
  }

  .delta-map-row {
    display: none;
  }

  .delta-map-row.is-active {
    display: grid;
    grid-template-columns: auto 1fr auto;
    min-height: 44px;
    padding: 4px 14px;
    border: 0;
    border-top: 3px solid var(--delta-teal);
  }

  .delta-map-row.is-active .delta-map-number::after {
    content: " / 04";
  }

  .delta-stylometry-orientation {
    margin-top: 28px;
  }

  .delta-method ol {
    grid-template-columns: 1fr;
  }

  .delta-method-step {
    min-height: 0;
  }

  .delta-style-trace {
    grid-template-columns: 1fr;
  }

  .delta-style-trace figcaption,
  .delta-trace-samples,
  .delta-trace-key {
    grid-column: 1;
    grid-row: auto;
  }

  .delta-context-strip {
    display: block;
  }

  .delta-context-strip p {
    margin-top: 4px;
  }

  .delta-readiness-band {
    grid-template-columns: auto minmax(0, 1fr);
    padding: 12px;
  }

  .delta-readiness-counts {
    grid-column: 2;
    justify-content: flex-start;
    white-space: normal;
  }

  .delta-review-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .delta-review-metric {
    min-height: 92px;
  }

  .delta-method-key {
    margin-top: 8px;
  }

  .delta-footer {
    grid-template-columns: 1fr;
    gap: 10px;
  }
}
</style>
"""
)
