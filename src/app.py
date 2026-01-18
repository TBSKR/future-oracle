"""
FutureOracle Dashboard

Streamlit-based dashboard for monitoring breakthrough investments.
"""

import streamlit as st
import yaml
from pathlib import Path

# Page config
st.set_page_config(
    page_title="FutureOracle",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        ["📊 Overview", "📰 News Feed", "🧠 Analysis", "💼 Portfolio", "🔮 Forecasts"]
    )
    
    st.markdown("---")
    st.subheader("Watchlist")
    
    # Display watchlist
    for stock in watchlist_config.get("public_stocks", []):
        st.markdown(f"**{stock['ticker']}** - {stock['name']}")

# Main content area
if page == "📊 Overview":
    st.header("Market Overview")
    st.info("🚧 Week 1: Dashboard skeleton created. Market data integration coming soon.")
    
    # Placeholder for watchlist performance
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Portfolio Value", "$0", "0%")
    with col2:
        st.metric("Daily Change", "$0", "0%")
    with col3:
        st.metric("Total Return", "0%", "0%")
    
    st.markdown("### Watchlist Performance")
    st.write("Real-time stock data will be displayed here using yfinance integration.")

elif page == "📰 News Feed":
    st.header("Breakthrough News Feed")
    st.info("🚧 Week 2: Scout Agent will populate this feed with curated breakthrough signals.")
    st.write("News articles filtered for humanoid robotics, longevity, AGI, and semiconductor breakthroughs.")

elif page == "🧠 Analysis":
    st.header("Grok Deep Analysis")
    st.info("🚧 Week 3: Analyst Agent summaries and impact scores will appear here.")
    st.write("AI-powered investment analysis with scenario modeling.")

elif page == "💼 Portfolio":
    st.header("Portfolio Tracker")
    st.info("🚧 Week 1: Add paper portfolio input functionality.")
    
    st.subheader("Add Holdings")
    with st.form("add_holding"):
        ticker = st.text_input("Ticker Symbol")
        shares = st.number_input("Number of Shares", min_value=0.0, step=0.01)
        avg_price = st.number_input("Average Price", min_value=0.0, step=0.01)
        submitted = st.form_submit_button("Add Holding")
        
        if submitted:
            st.success(f"Added {shares} shares of {ticker} at ${avg_price}")

elif page == "🔮 Forecasts":
    st.header("Scenario Forecasts")
    st.info("🚧 Week 4: Forecaster Agent will generate long-term wealth projections.")
    st.write("Base/Bull/Super-Bull scenarios with age-based milestones.")

# Footer
st.markdown("---")
st.caption("FutureOracle v0.1 | Built with Streamlit + CrewAI + Grok 4")
