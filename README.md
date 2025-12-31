# tax-copilot

**tax-copilot** is an AI-powered assistant that helps you collect and organize your personal tax information through intelligent conversation — **it does NOT file taxes**.

It uses a dynamic questioning agent to gather accurate tax data, adapting questions based on your responses to build a complete tax profile.

> ⚠️ Disclaimer: tax-copilot is for informational purposes only and is not tax, legal, or financial advice.
> Always verify with official sources or a qualified tax professional.

---

## What it does

### Pure Agentic Approach

tax-copilot is a **pure agentic system** with no hardcoded rules. Instead of following rigid checklists, it uses LLM to:

1. **Conduct intelligent interviews** - Ask contextual questions that adapt to your situation
2. **Extract structured data** - Convert conversational responses into validated tax profiles
3. **Provide flexible guidance** - Understand nuances and handle edge cases dynamically

### Features

#### 1. Precheck Mode (Dynamic Questioning)

The **Dynamic Questioning Agent** conducts a conversational tax interview:

- **Contextual follow-ups**: Questions adapt based on your previous answers
- **Natural language understanding**: Answer in plain English, no forms or codes
- **Session persistence**: Pause and resume interviews anytime
- **Confidence tracking**: System tracks certainty of extracted data
- **Local storage**: All data stays on your machine in `~/.tax_copilot/`

**Example conversation:**
```
Agent: Let's start with your income. Did you have a W-2 job in 2024?
You: Yes, I worked at two companies

Agent: Got it! Did you work at both companies for the full year, or
       did you change jobs mid-year?
You: I switched in June

Agent: Thanks. Just to confirm - was there any gap between jobs, or
       did you transition directly?
You: No gap, started the new job the next week
```

#### 2. Advisory Mode (Tax Analysis & Optimization)

After collecting your tax information, **Advisory Mode** provides:

- **Tax calculation**: Estimated federal and state tax liability
- **Optimization strategies**: 3-5 actionable recommendations to reduce taxes
- **Missed deductions**: Identifies potential deductions/credits you may have overlooked
- **Personalized report**: Professional advisory report with specific action items

**What you get:**
- Estimated tax liability with effective and marginal rates
- Prioritized tax-saving strategies (IRA contributions, bunching donations, etc.)
- Potential savings analysis
- Action plan with specific deadlines
- Interactive mode for follow-up questions

---

## What it does NOT do

- ❌ e-file or submit to IRS/state
- ❌ replace TurboTax / FreeTaxUSA / a CPA
- ❌ provide legally binding tax advice

tax-copilot provides **planning estimates** to help you understand your tax situation. Always consult a licensed tax professional for filing decisions.

---

## Quickstart

### Prerequisites
- Python 3.11+
- Anthropic API key (Claude) or OpenAI API key (GPT)

### 1) Setup
```bash
git clone https://github.com/<your-org>/tax-copilot.git
cd tax-copilot
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .
```

### 2) Configure API Key

Create a `.env` file in the project root:
```bash
# Copy example and edit with your key
cp .env.example .env
```

Edit `.env` and add your API key:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
# Or for OpenAI:
OPENAI_API_KEY=sk-your-key-here
```

Get API keys:
- Anthropic (Claude): https://console.anthropic.com/
- OpenAI (GPT): https://platform.openai.com/api-keys

### 3) Run Your First Interview

Start collecting tax information:
```bash
tax-copilot precheck --user john --year 2024
```

The agent will guide you through a conversational interview, asking about:
- Filing status
- Income sources (W-2, self-employment, investments)
- Deductions (student loans, itemized deductions)
- Dependents
- Other relevant tax information

**Commands during interview:**
- Type your answers naturally
- Type `exit` or `quit` to pause
- Press `Ctrl+C` to interrupt

### 4) Resume a Paused Interview

If you exit an interview, resume it later:
```bash
# List your sessions
tax-copilot precheck --list

# Resume a specific session
tax-copilot precheck --session sess_20240115_103000_abc123
```

### 5) View Your Tax Profile

After completing an interview:
```bash
# View summary
tax-copilot profile --user john --year 2024

# Export to JSON
tax-copilot profile --user john --year 2024 --format json --out profile.json
```

### 6) Analyze Your Tax Situation (Advisory Mode)

Get tax analysis and optimization recommendations:
```bash
# Analyze latest profile
tax-copilot analyze --user john

# Save the report to disk
tax-copilot analyze --user john --save

# Interactive mode (answer follow-up questions)
tax-copilot analyze --user john --interactive

# Export to JSON
tax-copilot analyze --user john --output json > analysis.json
```

The analysis will:
1. Calculate your estimated federal and state taxes
2. Identify 3-5 optimization strategies
3. Suggest potentially missed deductions
4. Generate a comprehensive advisory report

### 7) View Saved Reports

List and view your advisory reports:
```bash
# List all reports
tax-copilot reports

# List reports for specific user
tax-copilot reports --user john

# View specific report
tax-copilot reports --report-id rpt_20241228_abc123
```

---

## CLI Reference

### `tax-copilot precheck`

Start or continue a tax interview.

**Start new interview:**
```bash
tax-copilot precheck --user <user_id> --year <tax_year>
```

**Resume existing:**
```bash
tax-copilot precheck --session <session_id>
```

**List sessions:**
```bash
tax-copilot precheck --list [--user <user_id>] [--year <tax_year>]
```

**Force complete stuck session:**
```bash
tax-copilot precheck --session <session_id> --force-complete
```

**Options:**
- `--llm-provider`: Choose LLM provider (`anthropic` or `openai`, default from env or `openai`)

### `tax-copilot profile`

View or export saved tax profiles.

**View summary:**
```bash
tax-copilot profile --user <user_id> --year <tax_year>
```

**Export to JSON:**
```bash
tax-copilot profile --user <user_id> --year <tax_year> --format json --out profile.json
```

### `tax-copilot analyze`

Analyze tax profile and generate advisory report.

**Analyze latest profile:**
```bash
tax-copilot analyze --user <user_id>
```

**Analyze specific profile:**
```bash
tax-copilot analyze --profile-id <profile_id>
```

**Options:**
- `--interactive`: Enable follow-up questions about missed deductions
- `--save`: Save report to `~/.tax_copilot/reports/`
- `--output`: Output format (`markdown` or `json`, default: `markdown`)
- `--llm-provider`: Choose LLM provider (`anthropic` or `openai`)

### `tax-copilot reports`

List or view saved advisory reports.

**List all reports:**
```bash
tax-copilot reports
```

**Filter by user:**
```bash
tax-copilot reports --user <user_id>
```

**View specific report:**
```bash
tax-copilot reports --report-id <report_id>
```

**Options:**
- `--format`: Output format (`summary`, `markdown`, or `json`, default: `summary`)


### Running Tests

```bash
pip install -e ".[test]"
pytest
```

### Code Quality

```bash
pip install -e ".[dev]"

# Format code
black tax_copilot/

# Lint code
ruff check tax_copilot/
```

---

## Contributing

Contributions welcome! This project is in active development.

**Areas needing help:**
- Unit tests for agentic components
- Additional LLM provider integrations
- Document parsing (W-2, 1099 extraction)
- State-specific tax rules

---

## License

MIT License - see LICENSE file for details.

---

## Support

- **Issues**: https://github.com/garygangwu/tax-copilot/issues
- **Discussions**: https://github.com/garygangwu/tax-copilot/discussions
