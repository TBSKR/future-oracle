# 🔮 FutureOracle

**Your Grok-Powered Alpha Investment Engine**

FutureOracle is an AI-driven investment intelligence system designed to identify breakthrough opportunities in transformative technologies—humanoid robotics, longevity biotech, AGI/ASI, and next-gen semiconductors. Built for rapid iteration with AI agents (Claude, Cursor, Grok), minimal boilerplate, and maximum insight.

---

## 🎯 Vision

Track the future before it arrives. Monitor public and pre-IPO companies at the frontier of civilization-scale breakthroughs, generate deep alpha insights powered by Grok 4, and project long-term wealth scenarios tailored to your timeline.

**Core Focus Areas:**
- 🤖 Humanoid Robotics (Figure AI, Tesla Bot)
- 🧬 Longevity Biotech (Altos Labs, rejuvenation trials)
- 🧠 AGI/ASI Development (OpenAI, Anthropic, xAI)
- 💎 Next-Gen Semiconductors (NVDA, ASML)
- 🚀 Transformative Tech (PLTR, ISRG, SYM)

---

## 🏗️ Architecture

### Tech Stack
- **Frontend:** Streamlit (Python-native dashboard, free deployment)
- **Backend:** CrewAI multi-agent orchestration
- **Brain:** Grok 4 via xAI API for deep analysis
- **Data Sources:**
  - Stocks: `yfinance` (real-time market data)
  - News: NewsAPI.org + RSS feeds + X semantic search
  - Portfolio: SQLite (local) → broker APIs (future)
- **Scheduling:** Cron (daily/weekly runs)
- **Notifications:** Email (SMTP + Jinja templates), Discord webhooks
- **Deployment:** Local dev → Streamlit Cloud → VPS (Hetzner €5/mo)

### Multi-Agent System (CrewAI)

```
┌─────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR AGENT                     │
│              (Master Coordinator - Grok 4)               │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┼───────────┬───────────┬────────────┐
         ▼           ▼           ▼           ▼            ▼
    ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌─────────┐
    │ SCOUT  │  │ANALYST │  │CURATOR │  │REPORTER│  │GUARDIAN │
    │ AGENT  │  │ AGENT  │  │ AGENT  │  │ AGENT  │  │ AGENT   │
    └────────┘  └────────┘  └────────┘  └────────┘  └─────────┘
        │           │           │           │            │
        │           │           │           │            │
    News/RSS    Grok Deep   Dashboard   Weekly      Portfolio
    Filtering   Analysis    Summaries   Reports     Tracking
```

#### Agent Roles

1. **Orchestrator Agent** (Grok 4)
   - Daily/weekly workflow coordination
   - Delegates tasks to specialized agents
   - Compiles final outputs

2. **Scout Agent**
   - Monitors news, RSS, X for watchlist keywords
   - Filters breakthrough signals (humanoids, longevity, ASI)
   - Outputs: Ranked news items with relevance scores

3. **Analyst Agent** (Grok 4 Core)
   - Deep vibe check on Scout findings
   - Impact scoring (1-10), price predictions, risk flags
   - Generates optimistic/realistic/bull scenarios (5yr/10yr/20yr)

4. **Curator Agent**
   - Writes clean daily summaries (Markdown + Plotly charts)
   - Formats for dashboard consumption

5. **Reporter Agent**
   - Weekly HTML email generation
   - Charts, forecasts, portfolio snapshot, motivational wrap

6. **Portfolio Guardian**
   - Tracks holdings (paper or real broker integration)
   - Performance metrics, rebalance suggestions
   - Alerts via Discord/email

7. **Forecaster Agent** (Grok 4)
   - Scenario modeling: Base/Bull/Super-Bull returns
   - Age-based projections (e.g., "By age 31: €X in bull case")

---

## 📊 Watchlist

### Public Core (Liquid Markets)
- **NVDA** - NVIDIA (AI compute infrastructure)
- **TSLA** - Tesla (humanoid robotics, energy, autonomy)
- **ASML** - ASML (semiconductor lithography monopoly)
- **GOOGL** - Google/DeepMind (AGI research)
- **ISRG** - Intuitive Surgical (robotic surgery)
- **PLTR** - Palantir (AI platforms)
- **SYM** - Symbotic (warehouse automation)

### Private/Pre-IPO Track (News Alerts Only)
- **Figure AI** - Humanoid robotics
- **Anthropic** - Claude AGI development
- **xAI** - Grok/Musk AGI venture
- **OpenAI** - GPT/AGI frontier
- **Altos Labs** - Cellular rejuvenation

---

## 🚀 MVP Build Phases

### Week 1: Foundation
- [x] Project structure
- [ ] Streamlit skeleton
- [ ] `yfinance` tracker integration
- [ ] Basic watchlist dashboard
- [ ] Paper portfolio input

### Week 2: Agent Core
- [ ] CrewAI setup
- [ ] Scout Agent (news scraping)
- [ ] Grok API integration (test stub)
- [ ] Basic orchestration flow

### Week 3: Intelligence Layer
- [ ] Daily news summary generation
- [ ] Plotly chart integration
- [ ] Analyst Agent (Grok deep analysis)
- [ ] Dashboard polish

### Week 4: Reporting & Forecasts
- [ ] Weekly HTML email templates
- [ ] SMTP delivery setup
- [ ] Forecaster Agent (scenario modeling)
- [ ] Discord webhook alerts

### Ongoing Enhancements
- [ ] Real broker API integration (DEGIRO/Alpaca)
- [ ] Private stock IPO tracking
- [ ] Advanced scenario modeling
- [ ] Mobile-responsive dashboard

---

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.11+
- xAI API key ([get one here](https://x.ai/api))
- NewsAPI key ([free tier](https://newsapi.org/))
- Git & GitHub CLI

### Quick Start

```bash
# Clone repository
git clone https://github.com/TBSKR/future-oracle.git
cd future-oracle

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/.env.example config/.env
# Edit config/.env with your API keys

# Run dashboard
streamlit run src/app.py

# Run daily agent workflow
python scripts/run_daily.py
```

### Configuration

Edit `config/.env`:
```bash
# xAI Grok API
XAI_API_KEY=your_xai_key_here

# News Sources
NEWSAPI_KEY=your_newsapi_key_here

# Notifications
DISCORD_WEBHOOK_URL=your_webhook_url
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Portfolio (optional)
BROKER_API_KEY=your_broker_key
```

---

## 📁 Project Structure

```
future-oracle/
├── src/
│   ├── agents/              # CrewAI agent definitions
│   │   ├── orchestrator.py
│   │   ├── scout.py
│   │   ├── analyst.py
│   │   ├── curator.py
│   │   ├── reporter.py
│   │   ├── guardian.py
│   │   └── forecaster.py
│   ├── core/                # Core business logic
│   │   ├── grok_client.py   # xAI API wrapper
│   │   ├── portfolio.py     # Portfolio tracking
│   │   └── scenarios.py     # Forecast modeling
│   ├── data/                # Data fetching & storage
│   │   ├── market.py        # yfinance integration
│   │   ├── news.py          # News aggregation
│   │   └── db.py            # SQLite operations
│   ├── utils/               # Utilities
│   │   ├── notifications.py # Email/Discord
│   │   └── charts.py        # Plotly helpers
│   └── app.py               # Streamlit dashboard
├── config/
│   ├── .env.example         # Environment template
│   ├── watchlist.yaml       # Stock watchlist config
│   └── agents.yaml          # Agent prompts & settings
├── scripts/
│   ├── run_daily.py         # Daily cron job
│   └── run_weekly.py        # Weekly report
├── notebooks/               # Jupyter exploration
├── tests/                   # Unit tests
├── docs/                    # Additional documentation
│   ├── AGENTS.md            # Agent prompt engineering guide
│   ├── DEPLOYMENT.md        # VPS deployment guide
│   └── API_REFERENCE.md     # Code API docs
├── requirements.txt         # Python dependencies
├── .gitignore
└── README.md
```

---

## 🤖 AI Agent Development Guide

This project is **designed for AI-assisted development**. Whether you're using Claude, Cursor, Grok, or GitHub Copilot:

### For Claude/Cursor/AI Agents:

1. **Read First:**
   - `docs/AGENTS.md` - Agent prompt engineering patterns
   - `config/agents.yaml` - Current agent configurations
   - `src/agents/` - Existing agent implementations

2. **Development Workflow:**
   ```bash
   # Start with tests (TDD approach)
   # AI: "Write tests for Scout Agent news filtering"
   
   # Implement feature
   # AI: "Implement Scout Agent based on these tests"
   
   # Iterate
   # AI: "Refactor Scout Agent to use async/await"
   ```

3. **Key Patterns:**
   - All agents inherit from `BaseAgent` (see `src/agents/base.py`)
   - Grok API calls go through `GrokClient` wrapper
   - Use `@retry` decorator for API resilience
   - Log everything to `logs/` for debugging

4. **Prompt Templates:**
   - Stored in `config/agents.yaml`
   - Use Jinja2 syntax for dynamic prompts
   - Test prompts in `notebooks/` before deploying

---

## 📈 Usage Examples

### Dashboard
```bash
streamlit run src/app.py
# Open http://localhost:8501
```

### Manual Agent Run
```python
from src.agents import ScoutAgent, AnalystAgent
from src.core import GrokClient

# Initialize
grok = GrokClient()
scout = ScoutAgent()
analyst = AnalystAgent(grok)

# Run pipeline
news = scout.fetch_news(watchlist=["NVDA", "TSLA"])
analysis = analyst.analyze(news)
print(analysis)
```

### Scheduled Runs (Cron)
```bash
# Daily at 9 AM
0 9 * * * /path/to/venv/bin/python /path/to/scripts/run_daily.py

# Weekly Sunday 8 PM
0 20 * * 0 /path/to/venv/bin/python /path/to/scripts/run_weekly.py
```

---

## 🎨 Dashboard Preview

*(Screenshots coming in Week 3)*

- **Overview:** Watchlist performance, daily movers
- **News Feed:** Curated breakthrough signals
- **Analysis:** Grok deep-dive summaries
- **Portfolio:** Holdings, performance, rebalance suggestions
- **Forecasts:** 5yr/10yr/20yr scenario charts

---

## 🤝 Contributing

This is a personal alpha engine, but contributions welcome:

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

**AI Agent Contributors:** Include your prompt/workflow in PR description!

---

## 📜 License

MIT License - See [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

- **xAI** for Grok 4 API
- **CrewAI** for agent orchestration framework
- **Streamlit** for rapid dashboard prototyping
- **yfinance** for market data access

---

## 📞 Contact

Built by TBSKR - [GitHub](https://github.com/TBSKR)

**Disclaimer:** This is an experimental alpha research tool. Not financial advice. DYOR.

---

*"The best way to predict the future is to invest in it."* 🚀
