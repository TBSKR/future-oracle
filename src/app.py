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

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

from data.market import MarketDataFetcher
from data.db import Database
from core.portfolio import PortfolioManager
from core.grok_client import GrokClient
from agents.scout import ScoutAgent
from agents.analyst import AnalystAgent

# Page config
st.set_page_config(
    page_title="FutureOracle",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
@st.cache_resource
def init_components():
    """Initialize all components (cached)"""
    market = MarketDataFetcher()
    db = Database()
    portfolio = PortfolioManager(db)
    try:
        grok = GrokClient()
    except:
        grok = None
    scout = ScoutAgent()
    analyst = AnalystAgent(grok_client=grok)
    return market, db, portfolio, grok, scout, analyst

market, db, portfolio, grok, scout, analyst = init_components()

# Load configuration
config_path = Path(__file__).parent.parent / "config" / "watchlist.yaml"
with open(config_path, "r") as f:
    watchlist_config = yaml.safe_load(f)

# Check for high-impact alerts
@st.cache_data(ttl=300)  # Cache for 5 minutes
def check_high_impact_alerts():
    """Check for high-impact signals in the last 24 hours"""
    try:
        scout_result = scout.execute({"days_back": 1, "max_results": 10, "min_relevance": 7})
        if scout_result.get("success") and scout_result.get("articles"):
            analyst_result = analyst.execute({"articles": scout_result["articles"], "max_analyses": 5})
            if analyst_result.get("success"):
                high_impact = analyst.get_high_impact_signals(analyst_result["analyses"], threshold=8)
                return high_impact
    except Exception as e:
        st.error(f"Error checking alerts: {e}")
    return []

# Title and header
st.title("🔮 FutureOracle")
st.markdown("**Your Grok-Powered Alpha Investment Engine**")

# High-impact alert banner
high_impact_signals = check_high_impact_alerts()
if high_impact_signals:
    st.warning(f"🚨 **{len(high_impact_signals)} High-Impact Signal(s) Detected!** Check Daily Brief for details.")

st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Select View",
        ["📊 Overview", "📈 Watchlist", "📰 Daily Brief", "💼 Portfolio", "🔮 Forecasts", "🧪 Grok Test"]
    )
    
    st.markdown("---")
    st.subheader("Watchlist")
    
    # Display watchlist
    for stock in watchlist_config.get("public_stocks", []):
        ticker = stock['ticker']
        try:
            price = market.get_current_price(ticker)
            if price:
                st.markdown(f"**{ticker}** ${price:.2f}")
            else:
                st.markdown(f"**{ticker}** - {stock['name']}")
        except:
            st.markdown(f"**{ticker}** - {stock['name']}")
    
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# ========== OVERVIEW PAGE ==========
if page == "📊 Overview":
    st.header("Market Overview")
    
    # Portfolio metrics
    try:
        summary = portfolio.get_portfolio_summary()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Portfolio Value",
                f"${summary['total_value']:,.2f}",
                f"{summary['total_return_pct']:.2f}%"
            )
        with col2:
            st.metric(
                "Total Cost",
                f"${summary['total_cost']:,.2f}"
            )
        with col3:
            st.metric(
                "Total Return",
                f"${summary['total_return']:,.2f}",
                f"{summary['total_return_pct']:.2f}%"
            )
        with col4:
            st.metric(
                "Positions",
                summary['position_count']
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
    selected_ticker = st.selectbox("Select Stock", tickers)
    
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
            
            period = st.selectbox("Time Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
            
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

# ========== DAILY BRIEF PAGE ==========
elif page == "📰 Daily Brief":
    st.header("Daily Breakthrough Signals + Grok Analysis")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("**AI-curated news with deep Grok analysis**")
    
    with col2:
        days_back = st.selectbox("Days back", [1, 3, 7], index=0)
    
    with col3:
        max_analyses = st.selectbox("Max analyses", [3, 5, 10], index=1)
    
    # Fetch and analyze signals
    if st.button("🔍 Scan & Analyze", type="primary") or "analyses" not in st.session_state:
        with st.spinner("Scanning news sources..."):
            try:
                # Step 1: Scout
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
                
                st.success(f"✅ Scout: Found {len(articles)} signals (from {scout_result['total_fetched']} articles)")
                
                # Step 2: Analyst
                with st.spinner("Running Grok analysis..."):
                    analyst_result = analyst.execute({
                        "articles": articles,
                        "max_analyses": max_analyses
                    })
                    
                    if not analyst_result.get("success"):
                        st.error("Analyst Agent failed")
                        st.stop()
                    
                    analyses = analyst_result.get("analyses", [])
                    
                    # Sort by impact score
                    analyses.sort(key=lambda x: x.get("impact_score", 0), reverse=True)
                    
                    st.session_state.analyses = analyses
                    st.session_state.grok_available = analyst_result.get("grok_available", False)
                    
                    st.success(f"✅ Analyst: Completed {len(analyses)} deep analyses")
                    
                    # Cache to database
                    for article in articles:
                        try:
                            db.cache_scout_signal(article)
                        except:
                            pass
            
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.info("Make sure NEWSAPI_KEY and XAI_API_KEY are set in config/.env")
                st.stop()
    
    # Display analyses
    if "analyses" in st.session_state:
        analyses = st.session_state.analyses
        grok_available = st.session_state.get("grok_available", False)
        
        if not grok_available:
            st.warning("⚠️ Grok API unavailable - showing fallback analyses")
        
        st.markdown("---")
        
        # High-impact signals first
        high_impact = [a for a in analyses if a.get("impact_score", 0) >= 8]
        if high_impact:
            st.subheader(f"🚨 High-Impact Signals ({len(high_impact)})")
            for analysis in high_impact:
                _display_analysis_card(analysis, is_high_impact=True)
        
        # Regular signals
        regular = [a for a in analyses if a.get("impact_score", 0) < 8]
        if regular:
            st.subheader(f"📰 Breakthrough Signals ({len(regular)})")
            for analysis in regular:
                _display_analysis_card(analysis, is_high_impact=False)

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
    st.header("Scenario Forecasts")
    st.info("🚧 Week 4: Forecaster Agent will generate long-term wealth projections here.")
    
    st.markdown("""
    ### Coming Soon:
    - **Base Case:** Conservative 12% annual returns
    - **Bull Case:** Aggressive 25% annual returns  
    - **Super-Bull Case:** Breakthrough 50% annual returns
    - **Age-based milestones:** Projections for age 30, 35, 40
    - **Monte Carlo simulations:** Probability distributions
    """)

# ========== GROK TEST PAGE ==========
elif page == "🧪 Grok Test":
    st.header("Grok API Test")
    
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
st.caption(f"FutureOracle v0.3 | Week 2: Scout→Analyst Pipeline | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
