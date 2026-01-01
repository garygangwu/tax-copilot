# 🧮 Tax Copilot

**Your AI-Powered Tax Planning Assistant**

Tax Copilot is an intelligent tax consultant that combines conversational AI with expert tax analysis to help you understand, optimize, and plan your taxes — all through natural conversation.

```bash
# Get started in 3 commands
pip install -e .
tax-copilot precheck --user you --year 2024
tax-copilot analyze --user you --interactive
```

## 🎯 What You Get

- **💬 Smart Tax Interview** - No forms, just conversation. Answer questions naturally while AI extracts structured data
- **📊 Tax Calculation** - Instant federal and state tax estimates with effective and marginal rates
- **💡 Optimization Strategies** - 3-5 personalized recommendations to reduce your tax bill (IRA contributions, bunching, timing, etc.)
- **🔍 Missed Deductions** - AI identifies overlooked deductions and credits specific to your situation
- **📄 Professional Reports** - Get CPA-style advisory reports with action items and deadlines
- **💾 Complete Privacy** - All data stays on your machine, never sent to third parties

> ⚠️ **Disclaimer**: Tax Copilot is for informational and planning purposes only. It does NOT file taxes or provide legally binding advice. Always consult a qualified tax professional for filing decisions.

---

## 🚀 How It Works

Tax Copilot is a **pure agentic system** - no hardcoded rules or rigid checklists. Instead, it uses advanced LLMs to intelligently adapt to your unique tax situation:

### 1️⃣ Smart Data Collection (Precheck Mode)
Talk naturally about your finances. The AI asks contextual follow-up questions, understands nuances, and builds a complete tax profile.

### 2️⃣ Expert Analysis (Advisory Mode)
AI tax experts analyze your profile to:
- Calculate federal and state tax liability
- Identify optimization opportunities
- Find overlooked deductions and credits
- Generate actionable recommendations

### 3️⃣ Continuous Optimization
Interactive mode lets you explore "what-if" scenarios and get follow-up guidance on implementing strategies.

---

## ✨ Key Features

### 💬 Conversational Tax Interview (Precheck Mode)

Forget rigid forms. Just talk naturally about your finances:

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

**Features:**
- 🎯 **Contextual questions** that adapt to your situation
- 🗣️ **Plain English** - no tax jargon required
- ⏸️ **Pause & resume** anytime
- 📍 **Confidence tracking** - system knows what it's certain about
- 🔒 **Local storage** - data stays in `~/.tax_copilot/`

### 📊 Expert Tax Analysis (Advisory Mode)

Get professional-grade tax analysis and optimization recommendations:

**Tax Calculation**
- Federal and state tax liability estimates
- Effective and marginal tax rates
- Detailed breakdown (AGI, deductions, credits, etc.)

**Optimization Strategies** (3-5 personalized recommendations)
- Traditional IRA contributions
- Bunching charitable donations
- Tax-loss harvesting
- Timing strategies for income/deductions
- Estimated savings for each strategy

**Missed Deductions Finder**
- Identifies overlooked deductions and credits
- Follow-up questions to qualify you
- Requirements and documentation needed

**Example Output:**
```
╔════════════════════════════════════════════════════════════════╗
║                  2024 TAX ADVISORY REPORT                      ║
╚════════════════════════════════════════════════════════════════╝

Total Income: $85,000.00
Estimated Federal Tax: $12,750 (15% effective rate)
Estimated State Tax (CA): $3,825

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TOP OPTIMIZATION STRATEGIES

1. 💰 Maximize Traditional IRA - Est. Savings: $1,430
   → Contribute $7,000 to reduce taxable income
   → Deadline: April 15, 2025

2. 💵 Bunch Charitable Donations - Est. Savings: $800
   → Combine 2 years of donations into one
   → Only if you can itemize

Total Potential Savings: $2,230
```

---

## 🤔 Why Tax Copilot?

| Traditional Tax Software | Tax Copilot |
|-------------------------|-------------|
| Fill out rigid forms | Natural conversation |
| Generic advice for everyone | Personalized to your situation |
| Filing-focused only | Planning + optimization focused |
| Pay per return | Free and open source |
| Black box calculations | Transparent AI reasoning |

**Perfect for:**
- 💡 Tax planning and optimization (before filing)
- 📚 Understanding your tax situation
- 🔍 Finding deductions you might miss
- 💭 Exploring "what-if" scenarios
- 🎓 Learning about taxes through conversation

**Not a replacement for:**
- ❌ E-filing or IRS submission
- ❌ Legal tax advice from a CPA
- ❌ Tax preparation software (TurboTax, etc.)

Tax Copilot is a **planning companion** that helps you understand and optimize your taxes. Use it before filing season to maximize savings!

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- API key from [Anthropic](https://console.anthropic.com/) (Claude) or [OpenAI](https://platform.openai.com/api-keys) (GPT)

### Installation (2 minutes)

```bash
# Clone and setup
git clone https://github.com/garygangwu/tax-copilot.git
cd tax-copilot
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .

# Configure API key
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Usage

#### 1️⃣ Start a Tax Interview
```bash
tax-copilot precheck --user john --year 2024
```

Talk naturally about your income, deductions, and filing status. The AI will ask smart follow-up questions.

**Commands:** Type your answers naturally | `exit` to pause | `Ctrl+C` to stop

#### 2️⃣ Get Your Tax Analysis
```bash
tax-copilot analyze --user john --interactive
```

Get instant tax calculations, optimization strategies, and missed deduction alerts. Interactive mode lets you explore follow-up questions.

**Pro tip:** Use `--save` to keep a copy of your report!

#### 3️⃣ View & Export
```bash
# View your tax profile
tax-copilot profile --user john --year 2024

# List all advisory reports
tax-copilot reports --user john

# Export to JSON
tax-copilot analyze --user john --output json > analysis.json
```

### Quick Commands Cheat Sheet

```bash
# Resume a paused interview
tax-copilot precheck --list                    # See all sessions
tax-copilot precheck --session <session_id>    # Resume

# Analyze with options
tax-copilot analyze --user john --save         # Save report
tax-copilot analyze --user john --interactive  # Follow-up questions
tax-copilot analyze --profile-id <id>          # Analyze specific profile

# View reports
tax-copilot reports                            # List all
tax-copilot reports --user john                # Filter by user
tax-copilot reports --report-id <id>           # View specific report
```

---

## 🏗️ Architecture & Technology

Tax Copilot is built as a **pure agentic system** using advanced LLM capabilities:

### Multi-Agent Architecture
- **Questioning Agent** - Conducts dynamic interviews, adapts questions contextually
- **Data Organizer** - Extracts and structures information from conversational responses
- **Tax Calculator** - Computes federal and state tax liability using current tax code
- **Optimization Agent** - Identifies personalized tax-saving strategies
- **Deduction Finder** - Discovers overlooked deductions and credits

### Key Technologies
- **LLM Providers**: Anthropic Claude / OpenAI GPT
- **Structured Outputs**: JSON schema-based extraction for reliability
- **Session Management**: Persistent storage with resume capability
- **Confidence Tracking**: Per-field confidence scores for data quality

### Why Agentic?
Unlike traditional rule-based systems, Tax Copilot uses LLMs to:
- ✅ Understand nuanced tax situations
- ✅ Ask contextually relevant follow-up questions
- ✅ Handle edge cases without hardcoded logic
- ✅ Provide personalized explanations and reasoning
- ✅ Adapt to tax code changes without code updates

---

## 📚 CLI Reference

<details>
<summary><b>tax-copilot precheck</b> - Conversational tax interview</summary>

```bash
# Start new interview
tax-copilot precheck --user <user_id> --year <tax_year>

# Resume existing interview
tax-copilot precheck --session <session_id>

# List all sessions
tax-copilot precheck --list [--user <user_id>]

# Options
--llm-provider <anthropic|openai>  # Choose LLM provider
--force-complete                    # Force complete stuck session
```
</details>

<details>
<summary><b>tax-copilot analyze</b> - Generate tax advisory report</summary>

```bash
# Analyze latest profile
tax-copilot analyze --user <user_id>

# Analyze specific profile
tax-copilot analyze --profile-id <profile_id>

# Options
--interactive              # Enable follow-up Q&A
--save                    # Save report to disk
--output <markdown|json>  # Output format
--llm-provider            # Choose LLM provider
```
</details>

<details>
<summary><b>tax-copilot profile</b> - View/export tax profiles</summary>

```bash
# View summary
tax-copilot profile --user <user_id> --year <tax_year>

# Export to JSON
tax-copilot profile --user <user_id> --year <tax_year> --format json --out file.json
```
</details>

<details>
<summary><b>tax-copilot reports</b> - Manage advisory reports</summary>

```bash
# List all reports
tax-copilot reports [--user <user_id>]

# View specific report
tax-copilot reports --report-id <report_id>

# Options
--format <summary|markdown|json>  # Output format
```
</details>

---

## 🧪 Development

### Running Tests
```bash
pip install -e ".[test]"
pytest
```

### Code Quality
```bash
pip install -e ".[dev]"
black tax_copilot/        # Format
ruff check tax_copilot/   # Lint
```

---

## 🤝 Contributing

Contributions are welcome! Tax Copilot is in active development and there's lots to build.

### Priority Areas
- 🧪 **Testing**: Unit tests for agentic components
- 🔌 **Integrations**: Additional LLM providers (Gemini, local models)
- 📄 **Document Parsing**: Extract data from W-2, 1099 forms
- 🗺️ **State Tax Rules**: Better state-specific calculations
- 🌐 **UI**: Web interface for non-technical users
- 📊 **Visualizations**: Charts and graphs for tax breakdown

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

This is open source software. Use it freely, modify it, and share it. No warranties - use at your own risk!

---

## 💬 Support & Community

- 🐛 **Report Bugs**: [GitHub Issues](https://github.com/garygangwu/tax-copilot/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/garygangwu/tax-copilot/discussions)
- 📖 **Documentation**: Check the [docs](docs/) folder
- ⭐ **Star the Project**: Show your support!

---

**Remember**: Tax Copilot is a planning tool, not a tax filing service. Always consult a qualified tax professional for official advice.

**Happy tax planning! 🎉**
