"""
FutureOracle Dashboard

Streamlit-based dashboard for monitoring breakthrough investments.
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
    return market, db, portfolio, grok, scout

market, db, portfolio, grok, scout = init_components()

# Load configuration
config_path = Path(__file__).parent.parent / "config" / "watchlist.yaml"
with open(config_path, "r") as f:
    watchlist_config = yaml.safe_load(f)

# Title and header
st.title("🔮 FutureOracle")
st.markdown("**Your Grok-Powered Alpha Investment Engine**")
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
        price = market.get_current_price(ticker)
        if price:
            st.markdown(f"**{ticker}** ${price:.2f}")
        else:
            st.markdown(f"**{ticker}** - {stock['name']}")
    
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# ========== OVERVIEW PAGE ==========
if page == "📊 Overview":
    st.header("Market Overview")
    
    # Portfolio metrics
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
    
    st.markdown("---")
    
    # Watchlist performance
    st.subheader("Watchlist Performance")
    
    watchlist_data = []
    for stock in watchlist_config.get("public_stocks", []):
        ticker = stock['ticker']
        quote = market.get_quote(ticker)
        
        if quote.get("price"):
            watchlist_data.append({
                "Ticker": ticker,
                "Company": stock['name'],
                "Price": f"${quote['price']:.2f}",
                "Change": f"{quote.get('change_percent', 0):.2f}%",
                "Market Cap": f"${quote.get('market_cap', 0) / 1e9:.2f}B" if quote.get('market_cap') else "N/A"
            })
    
    if watchlist_data:
        st.dataframe(watchlist_data, use_container_width=True)
    else:
        st.info("Loading watchlist data...")

# ========== WATCHLIST PAGE ==========
elif page == "📈 Watchlist":
    st.header("Watchlist Deep Dive")
    
    # Ticker selector
    tickers = [stock['ticker'] for stock in watchlist_config.get("public_stocks", [])]
    selected_ticker = st.selectbox("Select Stock", tickers)
    
    if selected_ticker:
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
            for i, (period, ret) in enumerate(returns.items()):
                if ret is not None:
                    with return_cols[i]:
                        st.metric(period.upper(), f"{ret:.2f}%")

# ========== DAILY BRIEF PAGE ==========
elif page == "📰 Daily Brief":
    st.header("Daily Breakthrough Signals")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("**AI-curated news for your watchlist**")
    
    with col2:
        days_back = st.selectbox("Days back", [1, 3, 7], index=0)
    
    # Fetch signals
    with st.spinner("Scanning news sources..."):
        try:
            result = scout.execute({
                "days_back": days_back,
                "max_results": 15,
                "min_relevance": 6
            })
            
            if result.get("success"):
                articles = result.get("articles", [])
                
                st.success(f"Found {len(articles)} breakthrough signals (from {result['total_fetched']} articles)")
                
                # Display articles
                for article in articles:
                    with st.expander(f"⭐ {article['relevance_score']}/10 - {article['title']}", expanded=False):
                        col_a, col_b = st.columns([3, 1])
                        
                        with col_a:
                            st.markdown(f"**Source:** {article.get('source', 'Unknown')}")
                            st.markdown(f"**Published:** {article.get('published_at', 'Unknown')}")
                            st.markdown(f"**Summary:** {article.get('description', 'No summary available')}")
                            
                            if article.get('url'):
                                st.markdown(f"[Read full article]({article['url']})")
                        
                        with col_b:
                            st.markdown("**Matched Keywords:**")
                            for kw in article.get('matched_keywords', [])[:5]:
                                st.markdown(f"- {kw}")
                            
                            st.markdown(f"**Categories:**")
                            for cat in article.get('matched_categories', [])[:3]:
                                st.markdown(f"- {cat}")
                
                # Cache signals
                for article in articles:
                    db.cache_scout_signal(article)
            
            else:
                st.error("Failed to fetch news signals")
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Make sure NEWSAPI_KEY is set in config/.env")

# ========== PORTFOLIO PAGE ==========
elif page == "💼 Portfolio":
    st.header("Portfolio Tracker")
    
    # Get portfolio summary
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
st.caption(f"FutureOracle v0.2 | Week 1 Complete | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
