/* Playwright-inspired dark theme for pytest-html */

:root {
  --bg: #1e1e1e;
  --bg-elevated: #252526;
  --bg-row: #2d2d2d;
  --bg-row-alt: #252526;
  --border: #3c3c3c;
  --text: #cccccc;
  --text-muted: #9d9d9d;
  --text-strong: #f3f3f3;
  --accent: #2b4acb;
  --accent-soft: #3b82f6;
  --passed: #3dd68c;
  --failed: #f14c4c;
  --skipped: #e2c08d;
  --error: #f14c4c;
  --link: #79b8ff;
  --radius: 10px;
  --shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

@import url("https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap");

html {
  background: var(--bg);
}

body {
  font-family: "DM Sans", "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  min-width: 880px;
  max-width: 1280px;
  margin: 0 auto;
  padding: 28px 24px 64px;
  color: var(--text);
  background:
    radial-gradient(1200px 500px at 10% -10%, rgba(43, 74, 203, 0.28), transparent 55%),
    radial-gradient(900px 400px at 90% 0%, rgba(61, 214, 140, 0.08), transparent 50%),
    var(--bg);
}

h1 {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-strong);
  margin: 0 0 8px;
}

h2 {
  font-size: 15px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin: 28px 0 12px;
}

p {
  color: var(--text);
}

a {
  color: var(--link);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

/* Summary / environment cards */
#environment-header,
#results-table-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

#environment,
#results-table {
  width: 100%;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}

#environment td {
  padding: 10px 14px;
  border: 1px solid var(--border);
  vertical-align: top;
  color: var(--text);
}

#environment tr:nth-child(odd) {
  background-color: var(--bg-row);
}

#environment tr:nth-child(even) {
  background-color: var(--bg-row-alt);
}

#environment ul {
  margin: 0;
  padding: 0 18px;
}

/* Result colors */
span.passed,
.passed .col-result {
  color: var(--passed) !important;
  font-weight: 600;
}

span.skipped,
span.xfailed,
span.rerun,
.skipped .col-result,
.xfailed .col-result,
.rerun .col-result {
  color: var(--skipped) !important;
  font-weight: 600;
}

span.error,
span.failed,
span.xpassed,
.error .col-result,
.failed .col-result,
.xpassed .col-result {
  color: var(--failed) !important;
  font-weight: 700;
}

/* Results table */
#results-table {
  border-spacing: 0;
}

#results-table th {
  background: #1a1a1a;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  text-align: left;
}

#results-table td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
  vertical-align: top;
}

#results-table tr:nth-child(odd) {
  background: var(--bg-row);
}

#results-table tr:nth-child(even) {
  background: var(--bg-row-alt);
}

#results-table tbody tr:hover {
  background: #333333;
}

.col-testId {
  font-family: "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace;
  font-size: 12.5px;
  word-break: break-word;
}

.col-duration {
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
  white-space: nowrap;
}

.col-result {
  white-space: nowrap;
}

/* Trace / extras links as pills */
.col-links__extra {
  display: inline-flex;
  align-items: center;
  margin: 2px 6px 2px 0;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid var(--border);
  background: #1f2937;
  color: var(--link) !important;
  text-decoration: none !important;
}

.col-links__extra.url {
  border-color: rgba(59, 130, 246, 0.45);
  background: rgba(59, 130, 246, 0.12);
}

.col-links__extra.text {
  border-color: rgba(157, 157, 157, 0.35);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-muted) !important;
}

.col-links__extra:hover {
  filter: brightness(1.15);
}

/* Log / extras expansion */
.log,
.collapsed,
div[class*="log"] {
  font-family: "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace;
  font-size: 12px;
  background: #141414 !important;
  color: #d4d4d4 !important;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px !important;
}

/* Filter checkboxes area */
input[type="checkbox"] {
  accent-color: var(--accent-soft);
}

/* Make empty log less noisy looking */
.col-links:empty::after {
  content: "—";
  color: var(--text-muted);
}

/* Summary counts feel like badges */
#data-container span.passed,
#data-container span.failed,
#data-container span.skipped,
#data-container span.error {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
}
