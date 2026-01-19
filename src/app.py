"""
FutureOracle Dashboard

Streamlit-based dashboard for monitoring breakthrough investments.
Week 2: Integrated Scout → Analyst pipeline with Grok analysis.
"""

import streamlit as st
import yaml
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os
import logging
import uuid
from typing import Optional

# Suppress ScriptRunContext warnings from ThreadPoolExecutor threads
# These are harmless warnings that occur when using threading with Streamlit
class ScriptRunContextFilter(logging.Filter):
    def filter(self, record):
        return "missing ScriptRunContext" not in record.getMessage()

logging.getLogger("streamlit").addFilter(ScriptRunContextFilter())

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

# Validate required API keys on startup
required_keys = [
    "FINNHUB_API_KEY",
    "XAI_API_KEY", 
    "OPENAI_API_KEY",
    "PINECONE_API_KEY",
    "PINECONE_INDEX_NAME",
    "NEWSAPI_KEY"
]
missing_keys = [key for key in required_keys if not os.getenv(key)]

from data.market import MarketDataFetcher
from data.news import NewsAggregator
from data.db import Database
from core.portfolio import PortfolioManager
from core.grok_client import GrokClient
from memory.chat_memory import ChatMemory
from orchestrator import ChatOrchestrator

# CrewAI integration
try:
    from agents.crew_setup import create_analysis_crew, create_chat_crew
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    create_analysis_crew = None
    create_chat_crew = None

# Page config
st.set_page_config(
    page_title="FutureOracle",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== SESSION STATE INITIALIZATION ==========
def init_session_state():
    """Initialize session state with default values"""
    defaults = {
        # Watchlist and selections
        "watchlist": ['NVDA', 'TSLA', 'ASML', 'GOOGL', 'ISRG', 'PLTR', 'SYM'],
        "selected_ticker": 'NVDA',
        "selected_period": "6mo",

        # Analysis caching
        "analysis_cache": {},  # {ticker: {result: dict, timestamp: datetime, params: dict}}
        "last_analysis_timestamp": None,

        # Daily Brief selections
        "days_back": 1,
        "max_analyses": 5,

        # Chat state
        "chat_history": [],
        "user_profile": {"risk": None, "horizon": None},
        "user_plan": {},
        "onboarding_step": "ask_horizon",
        "chat_session_id": str(uuid.uuid4()),
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()

if "page" not in st.session_state:
    st.session_state.page = "💬 Chat (Home)"

if st.session_state.user_profile.get("risk") and st.session_state.user_profile.get("horizon"):
    st.session_state.onboarding_step = None

# Initialize components
@st.cache_resource
def init_components():
    """Initialize all components (cached)"""
    market = MarketDataFetcher()
    news = NewsAggregator()
    db = Database()
    portfolio = PortfolioManager(db)
    try:
        grok = GrokClient()
    except:
        grok = None

    # Lazy-import agents so the dashboard can still start even if optional
    # AI dependencies aren't installed in the environment.
    try:
        from agents.scout import ScoutAgent  # type: ignore
        scout = ScoutAgent()
    except Exception:
        scout = None

    try:
        from agents.analyst import AnalystAgent  # type: ignore
        analyst = AnalystAgent(grok_client=grok)
    except Exception:
        analyst = None

    try:
        from agents.forecaster import ForecasterAgent  # type: ignore
        forecaster = ForecasterAgent(grok_client=grok)
    except Exception:
        forecaster = None

    return market, db, portfolio, grok, scout, analyst, news, forecaster

market, db, portfolio, grok, scout, analyst, news, forecaster = init_components()

@st.cache_resource
def get_vector_memory():
    """Initialize Pinecone vector memory (cached). Returns None if unavailable."""
    try:
        from memory.vector_store import VectorMemory  # type: ignore
        return VectorMemory()
    except Exception as e:
        return None

def get_vector_memory_with_warning():
    """Get vector memory, showing warning if unavailable."""
    memory = get_vector_memory()
    if memory is None:
        st.warning("Pinecone unavailable - memory disabled")
    return memory

vector_memory = get_vector_memory()
chat_memory = ChatMemory(db, vector_memory)
chat_orchestrator = ChatOrchestrator(
    market=market,
    news=news,
    portfolio=portfolio,
    grok_client=grok,
    chat_memory=chat_memory,
    crew_available=CREWAI_AVAILABLE,
    crew_factory=create_chat_crew,
    scout=scout,
    analyst=analyst,
    forecaster=forecaster,
)

# Load configuration
config_path = Path(__file__).parent.parent / "config" / "watchlist.yaml"
with open(config_path, "r") as f:
    watchlist_config = yaml.safe_load(f)

def _build_watch_keywords(config: dict) -> list:
    keywords = []
    for stock in config.get("public_stocks", []):
        keywords.append(stock.get("ticker"))
        keywords.append(stock.get("name"))
        keywords.extend(stock.get("keywords", []))
    return [k for k in dict.fromkeys(keywords) if k]

watch_keywords = _build_watch_keywords(watchlist_config)

# Check for high-impact alerts
@st.cache_data(ttl=300)  # Cache for 5 minutes
def check_high_impact_alerts():
    """Check for high-impact signals in the last 24 hours"""
    if not scout or not analyst:
        return []
    try:
        scout_result = scout.execute({"days_back": 1, "max_results": 10, "min_relevance": 7})
        if scout_result.get("success") and scout_result.get("articles"):
            analyst_result = analyst.execute({
                "articles": scout_result["articles"],
                "max_analyses": 5,
                "use_memory": False,
                "store_memory": False
            })
            if analyst_result.get("success"):
                high_impact = analyst.get_high_impact_signals(analyst_result["analyses"], threshold=8)
                return high_impact
    except Exception as e:
        st.error(f"Error checking alerts: {e}")
    return []

# Title and header
st.title("🔮 FutureOracle")
st.markdown("**Chat-first investment intelligence with explainability built in.**")

# High-impact alert banner
high_impact_signals = check_high_impact_alerts()
if high_impact_signals:
    st.warning(f"🚨 **{len(high_impact_signals)} High-Impact Signal(s) Detected!** Check Signals for details.")

st.markdown("---")

# ========== HELPER FUNCTIONS (must be defined before sidebar callbacks) ==========

ANALYSIS_CACHE_TTL_HOURS = 4

def get_cached_analysis(cache_key: str, days_back: int, max_analyses: int):
    """Retrieve cached analysis if valid and params match"""
    cache = st.session_state.get("analysis_cache", {})
    if cache_key not in cache:
        return None

    cached = cache[cache_key]
    cached_params = cached.get("params", {})

    # Check params match
    if cached_params.get("days_back") != days_back or cached_params.get("max_analyses") != max_analyses:
        return None

    # Check TTL
    cached_time = cached.get("timestamp")
    if cached_time:
        age_hours = (datetime.now() - cached_time).total_seconds() / 3600
        if age_hours < ANALYSIS_CACHE_TTL_HOURS:
            return cached.get("result")
    return None

def cache_analysis(cache_key: str, result: dict, days_back: int, max_analyses: int):
    """Store analysis result in session state"""
    st.session_state.analysis_cache[cache_key] = {
        "result": result,
        "timestamp": datetime.now(),
        "params": {"days_back": days_back, "max_analyses": max_analyses}
    }
    st.session_state.last_analysis_timestamp = datetime.now()

def clear_all_caches():
    """Clear all session state caches"""
    st.session_state.analysis_cache = {}
    st.session_state.last_analysis_timestamp = None
    st.session_state.analyses = []
    st.cache_data.clear()

def _append_chat_message(role: str, content: str) -> None:
    st.session_state.chat_history.append({"role": role, "content": content})

def _parse_onboarding_horizon(text: str) -> Optional[str]:
    lowered = text.lower()
    if "short" in lowered:
        return "short"
    if "medium" in lowered:
        return "medium"
    if "long" in lowered:
        return "long"
    return None

def _parse_onboarding_risk(text: str) -> Optional[str]:
    lowered = text.lower()
    if "low" in lowered or "conservative" in lowered:
        return "low"
    if "medium" in lowered or "balanced" in lowered:
        return "medium"
    if "high" in lowered or "aggressive" in lowered:
        return "high"
    return None

def _handle_onboarding(user_input: str) -> bool:
    step = st.session_state.onboarding_step
    if not step:
        return False

    if step == "ask_horizon":
        horizon = _parse_onboarding_horizon(user_input)
        if horizon:
            st.session_state.user_profile["horizon"] = horizon
            st.session_state.onboarding_step = "ask_risk"
            _append_chat_message(
                "assistant",
                "Got it. What’s your risk comfort: low, medium, or high?",
            )
        else:
            _append_chat_message(
                "assistant",
                "I didn’t catch that. Is your time horizon short, medium, or long?",
            )
        return True

    if step == "ask_risk":
        risk = _parse_onboarding_risk(user_input)
        if risk:
            st.session_state.user_profile["risk"] = risk
            st.session_state.onboarding_step = None
            _append_chat_message(
                "assistant",
                "Thanks. I’ll tailor guidance to your horizon and risk comfort.",
            )
        else:
            _append_chat_message(
                "assistant",
                "Please choose low, medium, or high risk comfort.",
            )
        return True

    return False

# Sidebar
with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Select View",
        [
            "💬 Chat (Home)",
            "📊 Overview",
            "📈 Watchlist",
            "📰 Signals",
            "💼 Portfolio",
            "🔮 Forecasts",
            "⚙️ Settings",
        ],
        key="page",
    )
    
    st.markdown("---")
    st.subheader("Watchlist")

    # Display watchlist with parallel fetching
    tickers = [s['ticker'] for s in watchlist_config.get("public_stocks", [])]
    with st.spinner("Loading prices..."):
        quotes = market.get_watchlist_snapshot(tickers)

    for stock, quote in zip(watchlist_config.get("public_stocks", []), quotes):
        ticker = stock['ticker']
        price = quote.get("price") if isinstance(quote, dict) else None
        if price:
            change = quote.get("change_percent", 0)
            color = "green" if change >= 0 else "red"
            st.markdown(f"**{ticker}** ${price:.2f} :{color}[({change:+.1f}%)]")
        else:
            st.markdown(f"**{ticker}** - {stock['name']}")

    st.markdown("---")

    # Cache controls
    if st.button("🗑️ Clear Cache", help="Clear all cached data"):
        clear_all_caches()
        st.success("Cache cleared!")
        st.rerun()

    # Cache status
    cache_count = len(st.session_state.get("analysis_cache", {}))
    if cache_count > 0:
        st.caption(f"📦 {cache_count} cached analyses")

    if st.session_state.get("last_analysis_timestamp"):
        age_mins = (datetime.now() - st.session_state.last_analysis_timestamp).total_seconds() / 60
        st.caption(f"⏱️ Last analysis: {age_mins:.0f}m ago")

    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

def _display_analysis_card(analysis: dict, is_high_impact: bool = False):
    """Helper function to display analysis card"""
    impact = analysis.get("impact_score", 0)
    sentiment = analysis.get("sentiment", "neutral")
    
    # Sentiment emoji
    sentiment_emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️"}.get(sentiment, "➡️")
    
    # Impact badge
    if is_high_impact:
        badge = "⚡"
    elif impact >= 7:
        badge = "⭐"
    else:
        badge = "📌"
    
    title = f"{badge} {impact}/10 {sentiment_emoji} - {analysis['article_title']}"
    
    with st.expander(title, expanded=is_high_impact):
        col_a, col_b = st.columns([2, 1])
        
        with col_a:
            st.markdown(f"**Source:** {analysis.get('article_source', 'Unknown')}")
            st.markdown(f"**Sentiment:** {sentiment.upper()}")
            st.markdown(f"**30-Day Outlook:** {analysis.get('price_target_30d', 'N/A')}")
            st.markdown(f"**Key Insight:** {analysis.get('key_insight', 'N/A')}")
            
            if analysis.get('article_url'):
                st.markdown(f"[Read full article]({analysis['article_url']})")
        
        with col_b:
            st.metric("Impact Score", f"{impact}/10")
            st.metric("Relevance", f"{analysis.get('relevance_score', 0)}/10")
            
            if analysis.get("is_fallback"):
                st.warning("⚠️ Fallback analysis")
        
        # Risks
        risks = analysis.get("risks", [])
        if risks:
            st.markdown("**⚠️ Risk Flags:**")
            for risk in risks:
                st.markdown(f"- {risk}")
        
        # Scenarios
        scenarios = analysis.get("scenarios", {})
        if scenarios and any(v != "N/A" for v in scenarios.values()):
            st.markdown("**🔮 Long-Term Scenarios:**")
            for timeframe, scenario in scenarios.items():
                if scenario != "N/A":
                    st.markdown(f"- **{timeframe}:** {scenario}")

# ========== CHAT PAGE ==========
if page == "💬 Chat (Home)":
    col_chat, col_context = st.columns([3, 1])

    with col_chat:
        if not st.session_state.chat_history:
            if st.session_state.onboarding_step:
                greeting = (
                    "Welcome to FutureOracle. Ask me anything about markets, signals, or your portfolio.\n\n"
                    "To tailor risk framing, what’s your time horizon: short, medium, or long?"
                )
            else:
                greeting = (
                    "Welcome to FutureOracle. Ask me anything about markets, signals, or your portfolio."
                )
            _append_chat_message("assistant", greeting)

        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        user_input = st.chat_input("Ask about today’s signals, a ticker, or your plan…")
        if user_input:
            _append_chat_message("user", user_input)

            handled = _handle_onboarding(user_input)
            if not handled:
                response = chat_orchestrator.handle_message(
                    user_input,
                    {
                        "session_id": st.session_state.chat_session_id,
                        "user_profile": st.session_state.user_profile,
                        "user_plan": st.session_state.user_plan,
                        "known_tickers": [s["ticker"] for s in watchlist_config.get("public_stocks", [])],
                        "watch_keywords": watch_keywords,
                    },
                )
                st.session_state.user_profile = response["profile"]
                st.session_state.user_plan = response["plan"]
                _append_chat_message("assistant", response["response"])

            st.rerun()

    with col_context:
        st.subheader("Context Panel")
        st.markdown("**Data health**")
        if missing_keys:
            for key in required_keys:
                ok = key not in missing_keys
                st.markdown(f"{'✅' if ok else '⚠️'} {key}")
        else:
            st.markdown("✅ All API keys configured")
        last_refresh = st.session_state.get("last_analysis_timestamp")
        if last_refresh:
            st.caption(f"Last refresh: {last_refresh.strftime('%H:%M:%S')}")
        else:
            st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")

        st.markdown("---")
        st.markdown("**Portfolio snapshot**")
        try:
            summary = portfolio.get_portfolio_summary()
            st.metric("Total Value", f"€{summary.get('total_value', 0):,.0f}")
            st.caption(f"Positions: {summary.get('position_count', 0)}")
        except Exception as exc:
            st.caption(f"Portfolio unavailable: {exc}")

        st.markdown("---")
        st.markdown("**Today's top signal**")
        if high_impact_signals:
            top_signal = high_impact_signals[0]
            st.markdown(f"**{top_signal.get('article_title', 'Signal')}**")
            st.caption(top_signal.get("key_insight", "High-impact signal detected."))
        else:
            st.caption("No high-impact signals detected.")

        st.markdown("---")
        st.markdown("**Suggested navigation**")
        if st.button("Open Signals", use_container_width=True, key="nav_signals"):
            st.session_state.page = "📰 Signals"
            st.rerun()
        if st.button("Open Portfolio", use_container_width=True, key="nav_portfolio"):
            st.session_state.page = "💼 Portfolio"
            st.rerun()
        if st.button("Open Forecasts", use_container_width=True, key="nav_forecasts"):
            st.session_state.page = "🔮 Forecasts"
            st.rerun()

# ========== OVERVIEW PAGE ==========
elif page == "📊 Overview":
    st.header("Market Overview")
    
    # Portfolio metrics
    try:
        summary = portfolio.get_portfolio_summary()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Portfolio Value",
                f"${summary.get('total_value', 0):,.2f}",
                f"{summary.get('total_return_pct', 0):.2f}%"
            )
        with col2:
            st.metric(
                "Total Cost",
                f"${summary.get('total_cost', 0):,.2f}"
            )
        with col3:
            st.metric(
                "Total Return",
                f"${summary.get('total_return', 0):,.2f}",
                f"{summary.get('total_return_pct', 0):.2f}%"
            )
        with col4:
            st.metric(
                "Positions",
                summary.get('position_count', portfolio.position_count)
            )
    except Exception as e:
        st.error(f"Error loading portfolio: {e}")
        summary = {"total_value": 0, "total_cost": 0, "total_return": 0, "total_return_pct": 0, "position_count": 0}
    
    st.markdown("---")
    
    # High-impact signals section
    if high_impact_signals:
        st.subheader("🚨 High-Impact Signals (Impact ≥ 8/10)")
        for signal in high_impact_signals[:3]:
            with st.expander(f"⚡ {signal['impact_score']}/10 - {signal['article_title']}", expanded=True):
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.markdown(f"**Sentiment:** {signal['sentiment'].upper()}")
                    st.markdown(f"**Key Insight:** {signal['key_insight']}")
                    if signal.get('article_url'):
                        st.markdown(f"[Read article]({signal['article_url']})")
                with col_b:
                    st.metric("Impact Score", f"{signal['impact_score']}/10")
                    st.metric("Relevance", f"{signal['relevance_score']}/10")
    
    st.markdown("---")
    
    # Watchlist performance
    st.subheader("Watchlist Performance")
    
    try:
        watchlist_data = []
        for stock in watchlist_config.get("public_stocks", []):
            ticker = stock['ticker']
            try:
                quote = market.get_quote(ticker)
                
                if quote.get("price"):
                    watchlist_data.append({
                        "Ticker": ticker,
                        "Company": stock['name'],
                        "Price": f"${quote['price']:.2f}",
                        "Change": f"{quote.get('change_percent', 0):.2f}%",
                        "Market Cap": f"${quote.get('market_cap', 0) / 1e9:.2f}B" if quote.get('market_cap') else "N/A"
                    })
            except Exception as e:
                st.warning(f"Could not fetch data for {ticker}: {e}")
        
        if watchlist_data:
            st.dataframe(watchlist_data, use_container_width=True)
        else:
            st.info("Loading watchlist data...")
    except Exception as e:
        st.error(f"Error loading watchlist: {e}")

# ========== WATCHLIST PAGE ==========
elif page == "📈 Watchlist":
    st.header("Watchlist Deep Dive")
    
    # Ticker selector
    tickers = [stock['ticker'] for stock in watchlist_config.get("public_stocks", [])]

    # Ensure selected ticker is valid
    if st.session_state.selected_ticker not in tickers:
        st.session_state.selected_ticker = tickers[0] if tickers else None

    selected_ticker = st.selectbox(
        "Select Stock",
        tickers,
        index=tickers.index(st.session_state.selected_ticker) if st.session_state.selected_ticker in tickers else 0,
        key="ticker_select"
    )
    st.session_state.selected_ticker = selected_ticker
    
    if selected_ticker:
        try:
            # Get stock info
            stock_info = next((s for s in watchlist_config['public_stocks'] if s['ticker'] == selected_ticker), None)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader(f"{selected_ticker} - {stock_info['name']}")
                st.markdown(f"**Category:** {stock_info['category']}")
                st.markdown(f"**Thesis:** {stock_info['thesis']}")
            
            with col2:
                quote = market.get_quote(selected_ticker)
                if quote.get("price"):
                    st.metric("Current Price", f"${quote['price']:.2f}", f"{quote.get('change_percent', 0):.2f}%")
                    st.metric("52W Range", f"${quote.get('52w_low', 0):.2f} - ${quote.get('52w_high', 0):.2f}")
            
            # Historical chart
            st.subheader("Price History")
            
            PERIOD_OPTIONS = ["1mo", "3mo", "6mo", "1y", "2y"]
            period = st.selectbox(
                "Time Period",
                PERIOD_OPTIONS,
                index=PERIOD_OPTIONS.index(st.session_state.selected_period),
                key="period_select"
            )
            st.session_state.selected_period = period
            
            hist_data = market.get_historical_data(selected_ticker, period=period)
            
            if not hist_data.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist_data.index,
                    y=hist_data['Close'],
                    mode='lines',
                    name='Close Price',
                    line=dict(color='#00D9FF', width=2)
                ))
                
                fig.update_layout(
                    title=f"{selected_ticker} Price History ({period})",
                    xaxis_title="Date",
                    yaxis_title="Price (USD)",
                    template="plotly_dark",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No historical data available")
            
            # Returns table
            st.subheader("Returns")
            returns = market.calculate_returns(selected_ticker)
            
            if returns:
                return_cols = st.columns(6)
                for i, (period_key, ret) in enumerate(returns.items()):
                    if ret is not None:
                        with return_cols[i]:
                            st.metric(period_key.upper(), f"{ret:.2f}%")
        except Exception as e:
            st.error(f"Error loading {selected_ticker}: {e}")

# ========== SIGNALS PAGE ==========
elif page == "📰 Signals":
    st.header("Signals")
    st.caption("Daily brief and historical context")
    st.markdown("---")

    # Check if CrewAI is available with required keys
    xai_key_present = bool(os.getenv("XAI_API_KEY"))
    finnhub_key_present = bool(os.getenv("FINNHUB_API_KEY"))

    if CREWAI_AVAILABLE and xai_key_present and finnhub_key_present:
        st.success("CrewAI multi-agent system active")
        use_crewai = True
    elif CREWAI_AVAILABLE and not (xai_key_present and finnhub_key_present):
        missing = []
        if not xai_key_present:
            missing.append("XAI_API_KEY")
        if not finnhub_key_present:
            missing.append("FINNHUB_API_KEY")
        st.warning(f"CrewAI requires: {', '.join(missing)} - using legacy pipeline")
        use_crewai = False
    elif scout and analyst:
        st.info("Using Scout/Analyst pipeline")
        use_crewai = False
    else:
        st.error("No analysis agents available (missing dependencies).")
        st.info("Install requirements: pip install -r requirements.txt")
        st.stop()
    
    # Ticker selector for CrewAI analysis
    tickers = [stock['ticker'] for stock in watchlist_config.get("public_stocks", [])]
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if use_crewai:
            analysis_ticker = st.selectbox(
                "Select Ticker to Analyze",
                tickers,
                index=tickers.index(st.session_state.selected_ticker) if st.session_state.selected_ticker in tickers else 0,
                key="analysis_ticker_select"
            )
        else:
            st.markdown("**AI-curated news with Grok analysis**")
            analysis_ticker = None
    
    DAYS_OPTIONS = [1, 3, 7]
    MAX_OPTIONS = [3, 5, 10]

    with col2:
        days_back = st.selectbox(
            "Days back",
            DAYS_OPTIONS,
            index=DAYS_OPTIONS.index(st.session_state.days_back),
            key="days_back_select"
        )
        st.session_state.days_back = days_back

    with col3:
        max_analyses = st.selectbox(
            "Max analyses",
            MAX_OPTIONS,
            index=MAX_OPTIONS.index(st.session_state.max_analyses),
            key="max_analyses_select"
        )
        st.session_state.max_analyses = max_analyses
    
    # Fetch and analyze signals
    if st.button("🔍 Scan & Analyze", type="primary"):
        if use_crewai and analysis_ticker:
            # CrewAI path
            cache_key = f"crew_{analysis_ticker}"
            cached = get_cached_analysis(cache_key, days_back, max_analyses)

            if cached:
                st.info(f"Using cached CrewAI analysis from {st.session_state.last_analysis_timestamp.strftime('%H:%M')}")
                st.session_state.crew_result = cached
            else:
                try:
                    with st.spinner(f"Running CrewAI multi-agent analysis for {analysis_ticker}... (this may take 1-2 minutes)"):
                        crew = create_analysis_crew(analysis_ticker)
                        result = crew.kickoff()
                        
                        crew_result = {
                            "raw_output": str(result),
                            "ticker": analysis_ticker,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        st.session_state.crew_result = crew_result

                        memory = get_vector_memory()
                        if memory is not None:
                            try:
                                memory.store_analysis(
                                    ticker=analysis_ticker,
                                    analysis_text=crew_result["raw_output"],
                                    metadata={
                                        "timestamp": crew_result["timestamp"],
                                        "ticker": analysis_ticker,
                                        "analysis_type": "crewai",
                                        "summary": crew_result["raw_output"][:280]
                                    }
                                )
                            except Exception as e:
                                st.warning(f"Vector memory store skipped: {e}")
                        else:
                            st.warning("Pinecone unavailable - memory disabled")
                        
                        # Cache the result
                        cache_analysis(cache_key, crew_result, days_back, max_analyses)
                        
                    st.success(f"CrewAI analysis complete for {analysis_ticker}!")
                    
                except ValueError as e:
                    if "API_KEY" in str(e):
                        st.error(f"Missing API key: {str(e)}")
                        st.info("Set OPENAI_API_KEY and FINNHUB_API_KEY in config/.env")
                    else:
                        st.error(f"Configuration error: {str(e)}")
                    st.stop()
                except Exception as e:
                    error_msg = str(e)
                    if "rate limit" in error_msg.lower():
                        st.error("Finnhub API rate limit reached. Please wait a minute and try again.")
                    elif "invalid symbol" in error_msg.lower() or "not found" in error_msg.lower():
                        st.error(f"Invalid ticker symbol: {analysis_ticker}")
                    else:
                        st.error(f"CrewAI analysis failed: {error_msg}")
                    st.stop()
        else:
            # Legacy Scout/Analyst path
            cached = get_cached_analysis("daily_brief", days_back, max_analyses)

            if cached:
                st.info(f"Using cached analysis from {st.session_state.last_analysis_timestamp.strftime('%H:%M')}")
                st.session_state.analyses = cached.get("analyses", [])
                st.session_state.grok_available = cached.get("grok_available", False)
            else:
                try:
                    with st.spinner("🔍 Phase 1/2: Scanning news sources..."):
                        scout_result = scout.execute({
                            "days_back": days_back,
                            "max_results": 20,
                            "min_relevance": 6
                        })

                        if not scout_result.get("success"):
                            st.error("Scout Agent failed")
                            st.stop()

                        articles = scout_result.get("articles", [])

                        if not articles:
                            st.warning("No breakthrough signals found in the selected timeframe")
                            st.stop()

                    st.success(f"Scout: Found {len(articles)} signals")

                    with st.spinner("🧠 Phase 2/2: Running Grok analysis..."):
                        analyst_result = analyst.execute({
                            "articles": articles,
                            "max_analyses": max_analyses
                        })

                        if not analyst_result.get("success"):
                            st.error("Analyst Agent failed")
                            st.stop()

                        analyses = analyst_result.get("analyses", [])
                        analyses.sort(key=lambda x: x.get("impact_score", 0), reverse=True)

                        st.session_state.analyses = analyses
                        st.session_state.grok_available = analyst_result.get("grok_available", False)

                        cache_analysis("daily_brief", {
                            "analyses": analyses,
                            "grok_available": analyst_result.get("grok_available", False)
                        }, days_back, max_analyses)

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.info("Make sure NEWSAPI_KEY and XAI_API_KEY are set in config/.env")
                    st.stop()
    
    # Display CrewAI results
    if "crew_result" in st.session_state and st.session_state.crew_result:
        crew_result = st.session_state.crew_result
        ticker = crew_result.get("ticker", "Unknown")
        raw_output = crew_result.get("raw_output", "")
        
        st.markdown("---")
        st.subheader(f"CrewAI Analysis: {ticker}")
        
        # Display structured output in expandable sections
        with st.expander("📰 Scout Report - Market Intelligence", expanded=True):
            # Try to extract scout section from output
            if "scout" in raw_output.lower() or "news" in raw_output.lower():
                scout_end = raw_output.lower().find("analyst")
                if scout_end > 0:
                    st.markdown(raw_output[:scout_end])
                else:
                    st.markdown(raw_output[:len(raw_output)//3])
            else:
                st.markdown(raw_output[:1000] if len(raw_output) > 1000 else raw_output)
        
        with st.expander("📊 Analyst Assessment - Impact & Risks", expanded=True):
            # Try to extract analyst section
            analyst_start = raw_output.lower().find("analyst")
            analyst_end = raw_output.lower().find("forecast")
            if analyst_start > 0 and analyst_end > analyst_start:
                st.markdown(raw_output[analyst_start:analyst_end])
            elif analyst_start > 0:
                st.markdown(raw_output[analyst_start:analyst_start+1500])
            else:
                mid = len(raw_output)//3
                st.markdown(raw_output[mid:mid*2])
        
        with st.expander("🔮 Forecaster Scenarios - Long-Term Outlook", expanded=False):
            # Try to extract forecaster section
            forecast_start = raw_output.lower().find("forecast")
            if forecast_start > 0:
                st.markdown(raw_output[forecast_start:])
            else:
                st.markdown(raw_output[len(raw_output)*2//3:])
        
        # Full raw output option
        with st.expander("📄 Full Analysis Output", expanded=False):
            st.text(raw_output)
    
    # Display legacy analyses (if not using CrewAI)
    elif "analyses" in st.session_state and st.session_state.analyses:
        analyses = st.session_state.analyses
        grok_available = st.session_state.get("grok_available", False)
        
        if not grok_available:
            st.warning("Grok API unavailable - showing fallback analyses")
        
        st.markdown("---")
        
        high_impact = [a for a in analyses if a.get("impact_score", 0) >= 8]
        if high_impact:
            st.subheader(f"🚨 High-Impact Signals ({len(high_impact)})")
            for analysis in high_impact:
                _display_analysis_card(analysis, is_high_impact=True)
        
        regular = [a for a in analyses if a.get("impact_score", 0) < 8]
        if regular:
            st.subheader(f"📰 Breakthrough Signals ({len(regular)})")
            for analysis in regular:
                _display_analysis_card(analysis, is_high_impact=False)

    st.markdown("---")
    st.subheader("Historical Analyses")
    st.markdown("Explore prior analyses stored in Pinecone for deeper context.")

    memory = get_vector_memory()
    if memory is None:
        st.warning("Pinecone unavailable - memory disabled")
        st.info("Set PINECONE_API_KEY, PINECONE_INDEX_NAME, and OPENAI_API_KEY in config/.env")
        st.stop()

    tickers = [stock['ticker'] for stock in watchlist_config.get("public_stocks", [])]
    if not tickers:
        st.info("No watchlist tickers configured.")
        st.stop()

    selected_ticker = st.selectbox(
        "Select Ticker",
        tickers,
        index=tickers.index(st.session_state.selected_ticker) if st.session_state.selected_ticker in tickers else 0,
        key="historical_ticker_select"
    )

    query_text = st.text_input(
        "Search query",
        value=f"{selected_ticker} analysis"
    )
    top_k = st.slider("Results to fetch", min_value=1, max_value=25, value=10)

    if st.button("🔎 Load Historical Analyses"):
        with st.spinner("Querying Pinecone..."):
            matches = memory.retrieve_similar_analyses(
                query_text=query_text,
                top_k=top_k,
                ticker=selected_ticker
            )

        if not matches:
            st.info("No historical analyses found yet for this ticker.")
        else:
            def _parse_timestamp(value: str) -> datetime:
                try:
                    return datetime.fromisoformat(value)
                except Exception:
                    return datetime.min

            matches = sorted(
                matches,
                key=lambda m: _parse_timestamp(m.get("metadata", {}).get("timestamp", "")),
                reverse=True
            )

            for match in matches:
                metadata = match.get("metadata", {}) or {}
                timestamp = metadata.get("timestamp", "unknown")
                impact = metadata.get("impact_score", "N/A")
                sentiment = metadata.get("sentiment", "N/A")
                summary = (
                    metadata.get("summary")
                    or metadata.get("key_insight")
                    or metadata.get("analysis_text", "")
                ).strip()
                accuracy = metadata.get("prediction_accuracy", metadata.get("accuracy"))

                st.markdown(f"**{timestamp} | Impact {impact}/10 | Sentiment {sentiment}**")
                if summary:
                    st.markdown(summary)
                if accuracy is not None:
                    st.markdown(f"**Prediction Accuracy:** {accuracy}")

                with st.expander("Details"):
                    st.markdown(metadata.get("analysis_text") or "No stored analysis text.")

# ========== PORTFOLIO PAGE ==========
elif page == "💼 Portfolio":
    st.header("Portfolio Tracker")
    
    # Get portfolio summary
    try:
        summary = portfolio.get_portfolio_summary()
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Value", f"${summary['total_value']:,.2f}")
        with col2:
            st.metric("Total Cost", f"${summary['total_cost']:,.2f}")
        with col3:
            st.metric("Total Return", f"${summary['total_return']:,.2f}", f"{summary['total_return_pct']:.2f}%")
        
        st.markdown("---")
        
        # Holdings table
        st.subheader("Current Holdings")
        
        if summary['positions']:
            holdings_display = []
            for pos in summary['positions']:
                holdings_display.append({
                    "Ticker": pos['ticker'],
                    "Shares": f"{pos['shares']:.2f}",
                    "Avg Price": f"${pos['avg_price']:.2f}",
                    "Current Price": f"${pos['current_price']:.2f}" if pos['current_price'] else "N/A",
                    "Cost Basis": f"${pos['cost_basis']:,.2f}",
                    "Current Value": f"${pos['current_value']:,.2f}",
                    "Gain/Loss": f"${pos['gain_loss']:,.2f}",
                    "Return %": f"{pos['gain_loss_pct']:.2f}%"
                })
            
            st.dataframe(holdings_display, use_container_width=True)
            
            # Allocation pie chart
            st.subheader("Portfolio Allocation")
            allocation = portfolio.calculate_allocation()
            
            if allocation:
                fig = px.pie(
                    values=list(allocation.values()),
                    names=list(allocation.keys()),
                    title="Portfolio Allocation by Ticker"
                )
                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        
        else:
            st.info("No holdings yet. Add your first position below.")
        
        st.markdown("---")
        
        # Add holding form
        st.subheader("Add Position")
        
        with st.form("add_holding"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                ticker = st.text_input("Ticker Symbol", placeholder="NVDA").upper()
            with col2:
                shares = st.number_input("Number of Shares", min_value=0.01, step=0.01, value=1.0)
            with col3:
                avg_price = st.number_input("Average Price ($)", min_value=0.01, step=0.01, value=100.0)
            
            notes = st.text_area("Notes (optional)", placeholder="e.g., Long-term hold for AI revolution")
            
            submitted = st.form_submit_button("Add Position", type="primary")
            
            if submitted and ticker:
                try:
                    portfolio.add_position(ticker, shares, avg_price, notes=notes)
                    st.success(f"✅ Added {shares} shares of {ticker} at ${avg_price:.2f}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding position: {str(e)}")
    except Exception as e:
        st.error(f"Error loading portfolio: {e}")

# ========== FORECASTS PAGE ==========
elif page == "🔮 Forecasts":
    st.header("🔮 Long-Term Wealth Forecasts")
    st.markdown("**Personalized scenarios for your exponential wealth journey**")
    
    if not forecaster:
        st.error("Forecaster agent is unavailable (missing optional dependencies).")
        st.info("Fix by installing requirements into the active venv, then restart the app.")
        st.stop()
    
    # Initialize Forecaster
    if "forecaster" not in st.session_state:
        st.session_state.forecaster = forecaster
    forecaster = st.session_state.forecaster
    
    st.markdown("---")
    
    # Input form
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Your Investment Plan")
        current_age = st.number_input("Current Age", min_value=18, max_value=80, value=21, step=1)
        current_value = st.number_input("Current Portfolio Value (€)", min_value=0, value=0, step=1000)
        
    with col2:
        st.subheader("💰 Contribution Plan")
        monthly_contribution = st.number_input("Monthly Investment (€)", min_value=0, value=300, step=50)
        annual_bonus = st.number_input("Annual Bonus Investment (€)", min_value=0, value=1000, step=500)
    
    st.markdown("---")
    
    # Target ages
    st.subheader("🎯 Target Milestones")
    target_ages_input = st.text_input("Target Ages (comma-separated)", value="31, 41, 51")
    try:
        target_ages = [int(age.strip()) for age in target_ages_input.split(",")]
        target_ages = [age for age in target_ages if age > current_age]  # Filter future ages
    except:
        st.error("Invalid target ages format. Use comma-separated numbers (e.g., 31, 41, 51)")
        target_ages = [31, 41, 51]
    
    # Generate button
    if st.button("🚀 Generate Forecasts", type="primary"):
        with st.spinner("Generating personalized forecasts..."):
            result = forecaster.execute({
                "current_age": current_age,
                "current_value": current_value,
                "monthly_contribution": monthly_contribution,
                "annual_bonus": annual_bonus,
                "target_ages": target_ages
            })
            
            if result["success"]:
                st.session_state.forecast_result = result
                st.success(f"✅ Forecasts generated for {len(result['forecasts'])} milestones!")
                if not result["grok_available"]:
                    st.warning("⚠️ Using fallback calculations (Grok API unavailable)")
            else:
                st.error(f"❌ Forecast generation failed: {result.get('error', 'Unknown error')}")
    
    # Display results
    if 'forecast_result' in st.session_state and st.session_state.forecast_result.get("success"):
        result = st.session_state.forecast_result
        
        st.markdown("---")
        
        # Summary
        st.subheader("💡 Your Wealth Journey")
        st.info(result["summary"])
        
        st.markdown("---")
        
        # Forecast table
        st.subheader("📈 Scenario Breakdown")
        
        import pandas as pd
        
        table_data = []
        for forecast in result["forecasts"]:
            table_data.append({
                "Age": forecast["target_age"],
                "Years Ahead": forecast["years_ahead"],
                "Base Case": f"€{forecast['base_case']:,.0f}",
                "Bull Case": f"€{forecast['bull_case']:,.0f}",
                "Super-Bull Case": f"€{forecast['super_bull_case']:,.0f}"
            })
        
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Growth chart
        st.subheader("📊 Growth Trajectory")
        
        # Prepare data for chart
        ages = [current_age] + [f["target_age"] for f in result["forecasts"]]
        base_values = [current_value] + [f["base_case"] for f in result["forecasts"]]
        bull_values = [current_value] + [f["bull_case"] for f in result["forecasts"]]
        super_bull_values = [current_value] + [f["super_bull_case"] for f in result["forecasts"]]
        
        # Create Plotly chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=ages,
            y=base_values,
            mode='lines+markers',
            name='Base Case',
            line=dict(color='#3498db', width=3),
            marker=dict(size=10)
        ))
        
        fig.add_trace(go.Scatter(
            x=ages,
            y=bull_values,
            mode='lines+markers',
            name='Bull Case',
            line=dict(color='#f39c12', width=3),
            marker=dict(size=10)
        ))
        
        fig.add_trace(go.Scatter(
            x=ages,
            y=super_bull_values,
            mode='lines+markers',
            name='Super-Bull Case',
            line=dict(color='#2ecc71', width=3),
            marker=dict(size=10)
        ))
        
        fig.update_layout(
            title="Portfolio Value by Age",
            xaxis_title="Age",
            yaxis_title="Portfolio Value (€)",
            hovermode='x unified',
            height=500,
            template="plotly_dark"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Detailed scenarios
        st.subheader("📋 Detailed Scenarios")
        
        for forecast in result["forecasts"]:
            with st.expander(f"Age {forecast['target_age']} ({forecast['years_ahead']} years ahead)"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Base Case",
                        f"€{forecast['base_case']:,.0f}",
                        delta=None
                    )
                    if forecast.get("base_rationale"):
                        st.caption(forecast["base_rationale"])
                
                with col2:
                    st.metric(
                        "Bull Case",
                        f"€{forecast['bull_case']:,.0f}",
                        delta=None
                    )
                    if forecast.get("bull_rationale"):
                        st.caption(forecast["bull_rationale"])
                
                with col3:
                    st.metric(
                        "Super-Bull Case",
                        f"€{forecast['super_bull_case']:,.0f}",
                        delta=None
                    )
                    if forecast.get("super_bull_rationale"):
                        st.caption(forecast["super_bull_rationale"])
                
                if forecast.get("key_assumptions"):
                    st.markdown("**Key Assumptions:**")
                    for assumption in forecast["key_assumptions"]:
                        st.markdown(f"- {assumption}")
                
                if forecast.get("is_grok"):
                    st.caption("✨ Generated with Grok 4")
                else:
                    st.caption("🔢 Static calculation (Grok unavailable)")
        
        st.markdown("---")
        
        # Motivational footer
        st.success("🚀 **Remember:** The future is exponential. Stay invested in breakthrough tech, compound relentlessly, and think in decades.")
    
    else:
        st.info("👆 Enter your investment plan above and click 'Generate Forecasts' to see your personalized scenarios.")

# ========== SETTINGS PAGE ==========
elif page == "⚙️ Settings":
    st.header("Settings")

    st.subheader("API Key Status")
    for key in required_keys:
        ok = key not in missing_keys
        st.markdown(f"{'✅' if ok else '⚠️'} {key}")

    st.markdown("---")
    st.subheader("Grok API Test")

    if not grok:
        st.error("❌ Grok API not configured. Add XAI_API_KEY to config/.env")
        st.info("Get your API key from: https://x.ai/api")
    else:
        st.success("✅ Grok API client initialized")

        st.markdown("---")
        st.subheader("Test Prompt")

        # Predefined test prompts
        test_prompts = {
            "Humanoid Robotics Summary": "Summarize the latest developments in humanoid robotics and their investment implications in 2-3 sentences.",
            "NVIDIA Analysis": "Why is NVIDIA critical for the AI revolution? Provide a concise investment thesis.",
            "Longevity Biotech": "What are the most promising longevity biotech breakthroughs and which companies are leading?",
            "Custom": ""
        }

        prompt_choice = st.selectbox("Select test prompt", list(test_prompts.keys()))

        if prompt_choice == "Custom":
            user_prompt = st.text_area("Enter your prompt", height=100)
        else:
            user_prompt = test_prompts[prompt_choice]
            st.text_area("Prompt", user_prompt, height=100, disabled=True)

        if st.button("Send to Grok", type="primary"):
            if user_prompt:
                with st.spinner("Thinking..."):
                    try:
                        response = grok.analyze_with_prompt(
                            system_prompt="You are a visionary investment analyst focused on breakthrough technologies.",
                            user_prompt=user_prompt,
                            temperature=0.7,
                            max_tokens=500
                        )

                        st.markdown("### Grok Response:")
                        st.markdown(response)

                        st.success("✅ API call successful")

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("Please enter a prompt")

# Footer
st.markdown("---")
st.caption(f"FutureOracle v0.4 | Chat-first interface | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
