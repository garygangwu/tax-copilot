# tax-copilot

**tax-copilot** is an AI copilot that reviews your personal tax return like a CPA — **it does NOT file taxes**.

It helps individuals catch common mistakes, sanity-check year-over-year changes, and produce a “before you file” checklist.

> ⚠️ Disclaimer: tax-copilot is for informational purposes only and is not tax, legal, or financial advice.  
> Always verify with official sources or a qualified tax professional.

---

## What it does (MVP)

### 1) Baseline from last year (optional but recommended)
Upload last year’s return (e.g., Form 1040 PDF or a tax summary). tax-copilot extracts a baseline “tax profile” and assumptions.

### 2) Ingest this year’s documents
Upload this year’s W-2 / 1099s (or paste summaries).

### 3) CPA-style review rules
Runs a rules engine to detect:
- missing forms / mismatches
- high-risk areas (e.g., cost basis / common errors)
- suspicious year-over-year anomalies

### 4) Year-over-year sanity checks
Highlights major changes and asks for confirmations (CPA-style).

### 5) Output: Review report + “Before you file” checklist
Generates a structured report with severity levels:
- 🔴 High risk
- 🟡 Needs confirmation
- 🟢 FYI

---

## What it does NOT do
- ❌ e-file
- ❌ submit to IRS/state
- ❌ guarantee correct tax liability
- ❌ replace TurboTax / FreeTaxUSA / a CPA

tax-copilot is designed to complement existing filing tools.

---

## Quickstart

### Prerequisites
- Python 3.11+ (recommended)
- An LLM provider key (OpenAI-compatible or your own)

### 1) Setup
```bash
git clone https://github.com/<your-org>/tax-copilot.git
cd tax-copilot
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
