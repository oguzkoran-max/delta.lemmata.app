"""Delta's P002 visual system."""

APP_CSS = """
<style>
:root {
  --delta-ink: #18211f;
  --delta-muted: #5d6965;
  --delta-line: #83928c;
  --delta-canvas: #f7f8f7;
  --delta-paper: #ffffff;
  --delta-focus: #1769aa;
  /* Teal is the single accent wired into this stylesheet. Badge hues come from
     Streamlit's named palette and the link colour lives in
     .streamlit/config.toml, so no further accent tokens are defined here.
     --delta-teal-on-dark is a lightened teal for the dark sidebar, where the
     base teal fails WCAG AA contrast on #1c2925. */
  --delta-teal: #116f63;
  --delta-teal-on-dark: #63b6a6;
}

[data-testid="stAppViewContainer"] {
  background: var(--delta-canvas);
}

[data-testid="stMainBlockContainer"] {
  max-width: 1240px;
  padding-top: 2.4rem;
  padding-bottom: 2rem;
}

[data-testid="stHeader"] {
  display: none;
}

#MainMenu,
footer,
[data-testid="stAppDeployButton"],
[data-testid="stExpandSidebarButton"] {
  display: none;
}

[data-testid="stSidebar"] {
  background: #1c2925;
  border-right: 1px solid #31443d;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  color: #f0f5f2;
}

[data-testid="stSidebar"] [data-testid="stExpander"] {
  border-color: #456057;
  border-radius: 6px;
}

.delta-progress {
  width: 100%;
  height: 8px;
  overflow: hidden;
  margin: 0.45rem 0 0.9rem;
  border-radius: 4px;
  background: #f0f5f2;
}

.delta-progress-fill {
  display: block;
  width: 50%;
  height: 100%;
  background: var(--delta-teal-on-dark);
}

.delta-header {
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 0 1rem;
  border-bottom: 1px solid var(--delta-line);
  margin-bottom: 1.4rem;
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
  background: var(--delta-ink);
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
  min-height: 44px;
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
  color: var(--delta-teal-on-dark);
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
.st-key-review_stage,
.st-key-boundary_panel,
.st-key-evidence_panel,
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
input:focus-visible,
textarea:focus-visible,
[role="radio"]:focus-visible {
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
    flex-wrap: nowrap !important;
  }

  .st-key-research_purpose button[role="radio"] {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    height: 48px;
    padding-right: 0.35rem;
    padding-left: 0.35rem;
    font-size: 0.75rem;
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

@media (max-width: 340px) {
  [data-testid="stMainBlockContainer"] {
    padding-top: 0.375rem;
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
</style>
"""
