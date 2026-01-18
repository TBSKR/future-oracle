# 🤖 AI Agent Quick Start Guide

This guide is specifically designed for AI coding assistants (Claude, Cursor, GitHub Copilot, etc.) to quickly understand and contribute to the FutureOracle project.

---

## 🎯 Project Overview

**FutureOracle** is a multi-agent AI system for identifying breakthrough investment opportunities. It uses:
- **CrewAI** for agent orchestration
- **Grok 4** (via xAI API) for deep analysis
- **Streamlit** for the dashboard
- **yfinance** for market data
- **NewsAPI** for news aggregation

---

## 📂 Project Structure at a Glance

```
future-oracle/
├── src/
│   ├── agents/          # AI agent implementations (Scout, Analyst, etc.)
│   ├── core/            # Core logic (Grok client, portfolio, scenarios)
│   ├── data/            # Data fetching (market, news, database)
│   ├── utils/           # Utilities (notifications, charts)
│   └── app.py           # Streamlit dashboard
├── config/              # Configuration files (.env, watchlist.yaml, agents.yaml)
├── scripts/             # Cron job scripts (run_daily.py, run_weekly.py)
├── notebooks/           # Jupyter notebooks for experimentation
├── docs/                # Documentation
└── tests/               # Unit tests
```

---

## 🚀 Quick Start for AI Agents

### 1. Understanding the Codebase

**Key Files to Read First:**
1. `README.md` - Project overview and architecture
2. `config/agents.yaml` - Agent roles, prompts, and workflows
3. `config/watchlist.yaml` - Stocks and keywords to track
4. `docs/AGENTS.md` - Prompt engineering best practices
5. `src/agents/base.py` - Base class for all agents

**Key Concepts:**
- **Agents are stateless functions**: They receive context, perform a task, and return output.
- **All agents inherit from `BaseAgent`**: This provides logging, error handling, and configuration management.
- **Prompts are stored in `config/agents.yaml`**: Use Jinja2 templates for dynamic prompts.
- **Grok API calls go through `GrokClient`**: This wrapper handles retries and error handling.

### 2. Development Workflow

When asked to implement a feature or agent:

1. **Read the relevant documentation** (especially `docs/AGENTS.md`)
2. **Check existing implementations** in `src/agents/` for patterns
3. **Start with a Jupyter notebook** in `notebooks/` to experiment
4. **Write tests first** (TDD approach) in `tests/`
5. **Implement the feature** in the appropriate module
6. **Update configuration** in `config/` if needed
7. **Document your changes** in relevant docs

### 3. Common Tasks

#### Task: Implement a New Agent

**Steps:**
1. Create a new file in `src/agents/` (e.g., `scout.py`)
2. Inherit from `BaseAgent`
3. Implement the `execute(context)` method
4. Add the agent to `src/agents/__init__.py`
5. Add agent configuration to `config/agents.yaml`
6. Write tests in `tests/test_agents.py`

**Template:**
```python
from .base import BaseAgent
from typing import Dict, Any

class ScoutAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            name="Scout",
            role="Breakthrough Signal Hunter",
            goal="Monitor news for breakthrough signals",
            backstory="You scan thousands of news items daily...",
            config=config
        )
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation here
        pass
```

#### Task: Add a New Data Source

**Steps:**
1. Create a new module in `src/data/` (e.g., `twitter.py`)
2. Implement a class with methods to fetch data
3. Add configuration to `config/.env.example`
4. Update `docs/DEPLOYMENT.md` with setup instructions
5. Write tests in `tests/test_data.py`

#### Task: Modify the Dashboard

**Steps:**
1. Edit `src/app.py`
2. Use Streamlit components (st.metric, st.chart, st.dataframe, etc.)
3. Test locally with `streamlit run src/app.py`
4. Update screenshots in README if UI changes significantly

#### Task: Update Agent Prompts

**Steps:**
1. Edit `config/agents.yaml`
2. Test prompts in `notebooks/agent_development_example.ipynb`
3. Iterate based on Grok's responses
4. Document prompt changes in `docs/AGENTS.md`

---

## 🧪 Testing Your Changes

### Local Testing

```bash
# Test market data fetcher
python -c "from src.data.market import MarketDataFetcher; m = MarketDataFetcher(); print(m.get_quote('NVDA'))"

# Test news aggregator
python -c "from src.data.news import NewsAggregator; n = NewsAggregator(); print(len(n.fetch_news_for_keywords(['NVDA'], days_back=1)))"

# Test Grok client
python -c "from src.core.grok_client import GrokClient; g = GrokClient(); print(g.analyze_with_prompt('You are helpful', 'Say hi', max_tokens=20))"

# Run Streamlit dashboard
streamlit run src/app.py
```

### Running Scripts

```bash
# Daily workflow
python scripts/run_daily.py

# Weekly report
python scripts/run_weekly.py
```

---

## 📝 Code Style Guidelines

- **Follow PEP 8** for Python code
- **Use type hints** wherever possible
- **Write docstrings** for all classes and functions
- **Log important events** using `self.logger` in agents
- **Handle errors gracefully** with try/except blocks
- **Keep functions small and focused** (single responsibility principle)

---

## 🔑 Environment Variables

Key environment variables (see `config/.env.example` for full list):

- `XAI_API_KEY` - xAI Grok API key
- `NEWSAPI_KEY` - NewsAPI key
- `DISCORD_WEBHOOK_URL` - Discord webhook for notifications
- `SMTP_EMAIL` / `SMTP_PASSWORD` - Email credentials for reports

---

## 🐛 Common Issues & Solutions

### Issue: Import errors when running scripts
**Solution:** Make sure you're using the virtual environment and the project root is in `sys.path`

### Issue: Grok API returns errors
**Solution:** Check that `XAI_API_KEY` is set correctly in `.env` and the API is operational

### Issue: yfinance returns empty data
**Solution:** Check ticker symbol is correct and market is open (or use historical data)

### Issue: Streamlit dashboard won't load
**Solution:** Ensure `config/watchlist.yaml` exists and is valid YAML

---

## 📚 Additional Resources

- **CrewAI Docs:** https://docs.crewai.com/
- **xAI API Docs:** https://x.ai/api
- **Streamlit Docs:** https://docs.streamlit.io/
- **yfinance Docs:** https://pypi.org/project/yfinance/

---

## 🎯 Current Development Phase

**Week 1 (Current):** Foundation
- [x] Project structure
- [x] Configuration files
- [x] Base classes and utilities
- [ ] Streamlit dashboard integration with yfinance
- [ ] Paper portfolio input functionality

**Next Steps:**
- Integrate `MarketDataFetcher` into Streamlit dashboard
- Create portfolio tracking database schema
- Implement paper portfolio CRUD operations

---

## 💡 Tips for AI Agents

1. **Always check existing code first** before implementing something new
2. **Use the Jupyter notebook** to experiment before writing production code
3. **Follow the existing patterns** in the codebase (e.g., all agents inherit from `BaseAgent`)
4. **Update documentation** when you make changes
5. **Test incrementally** - don't write large chunks of code without testing
6. **Ask clarifying questions** if the requirements are ambiguous
7. **Reference `docs/AGENTS.md`** for prompt engineering best practices

---

This project is designed to be AI-agent-friendly. Happy coding! 🚀
