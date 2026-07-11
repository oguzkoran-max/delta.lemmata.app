"""Delta's P002 visual system."""

APP_CSS = """
<style>
:root {
  --delta-ink: #18211f;
  --delta-muted: #5d6965;
  --delta-line: #ccd6d1;
  --delta-canvas: #f4f6f5;
  --delta-paper: #ffffff;
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
  padding-top: 3.25rem;
  padding-bottom: 2rem;
}

[data-testid="stHeader"] {
  background: rgba(244, 246, 245, 0.96);
}

#MainMenu,
footer,
[data-testid="stAppDeployButton"] {
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
  margin-top: 0.4rem;
}

.delta-map-row {
  display: grid;
  grid-template-columns: 28px 1fr auto;
  gap: 0.65rem;
  align-items: center;
  min-height: 44px;
  border-bottom: 1px solid var(--delta-line);
}

.delta-map-row:last-child {
  border-bottom: 0;
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

.st-key-purpose_detail,
.st-key-corpus_stage,
.st-key-experiment_map,
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
  min-height: 42px;
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

h1 {
  font-size: 2rem;
  line-height: 1.18;
}

h2 {
  font-size: 1.25rem;
  line-height: 1.25;
}

h3 {
  font-size: 1rem;
  line-height: 1.3;
}

@media (max-width: 760px) {
  [data-testid="stMainBlockContainer"] {
    padding-left: 1rem;
    padding-right: 1rem;
    padding-top: 3rem;
  }

  .delta-header {
    align-items: flex-start;
    min-height: 64px;
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

  h1 {
    font-size: 1.65rem;
  }

  .delta-map-row {
    grid-template-columns: 24px 1fr auto;
  }
}
</style>
"""
