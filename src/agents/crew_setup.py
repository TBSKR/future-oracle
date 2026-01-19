"""
CrewAI Setup for FutureOracle

Defines agents, tools, tasks, and crew for multi-agent market analysis.
Uses CrewAI framework for orchestration and collaboration.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

from data.finnhub_client import FinnhubClient
from data.reddit_client import RedditClient
from data.market import MarketDataFetcher
from data.news import NewsAggregator


# Lazy-loaded Finnhub client
_finnhub_client: Optional[FinnhubClient] = None
_reddit_client: Optional[RedditClient] = None


def _get_xai_llm() -> LLM:
    """Get LLM configured for X.AI (Grok) API."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise ValueError("XAI_API_KEY not set")
    return LLM(
        model="xai/grok-beta",
        api_key=api_key,
        base_url="https://api.x.ai/v1"
    )


def _get_finnhub_client() -> FinnhubClient:
    """Get or create FinnhubClient instance."""
    global _finnhub_client
    if _finnhub_client is None:
        _finnhub_client = FinnhubClient()
    return _finnhub_client


def _get_reddit_client() -> RedditClient:
    """Get or create RedditClient instance."""
    global _reddit_client
    if _reddit_client is None:
        _reddit_client = RedditClient()
    return _reddit_client


# =============================================================================
# CUSTOM TOOLS
# =============================================================================

@tool
def finnhub_news_tool(ticker: str) -> str:
    """
    Fetch recent company news for a given stock ticker.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'NVDA', 'TSLA')
    
    Returns:
        JSON string containing list of news articles with headline, source, 
        datetime, url, and summary.
    """
    try:
        client = _get_finnhub_client()
        to_date = datetime.now()
        from_date = to_date - timedelta(days=7)
        
        news = client.get_news(ticker, from_date, to_date)
        
        formatted_news = []
        for article in news[:10]:
            formatted_news.append({
                "headline": article.get("headline", ""),
                "source": article.get("source", ""),
                "datetime": datetime.fromtimestamp(article.get("datetime", 0)).isoformat(),
                "url": article.get("url", ""),
                "summary": article.get("summary", "")[:500]
            })
        
        return json.dumps(formatted_news, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def finnhub_sentiment_tool(ticker: str) -> str:
    """
    Get social sentiment and buzz data for a given stock ticker.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'NVDA', 'TSLA')
    
    Returns:
        JSON string containing sentiment scores, buzz metrics, and 
        company news score.
    """
    try:
        client = _get_finnhub_client()
        sentiment = client.get_sentiment(ticker)
        
        result = {
            "ticker": ticker,
            "buzz": sentiment.get("buzz", {}),
            "sentiment": sentiment.get("sentiment", {}),
            "company_news_score": sentiment.get("companyNewsScore", 0),
            "sector_average_bullish_percent": sentiment.get("sectorAverageBullishPercent", 0),
            "sector_average_news_score": sentiment.get("sectorAverageNewsScore", 0)
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("Reddit Sentiment Tool")
def reddit_sentiment_tool(ticker: str) -> str:
    """Get Reddit sentiment for a stock ticker from r/wallstreetbets."""
    # TODO: Validate tool output in an end-to-end run once Reddit creds are set.
    if os.getenv("REDDIT_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        return "Reddit sentiment disabled via REDDIT_ENABLED"
    try:
        reddit = _get_reddit_client()
        mentions = reddit.get_ticker_mentions(ticker)
        sentiment_score = reddit.calculate_sentiment_score(mentions)
        return (
            f"Reddit mentions: {len(mentions)}, "
            f"Sentiment score: {sentiment_score:.2f}/100"
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def market_quote_tool(ticker: str) -> str:
    """Fetch latest quote data for a ticker."""
    try:
        market = MarketDataFetcher()
        return json.dumps(market.get_quote(ticker), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def market_history_tool(ticker: str, period: str = "6mo") -> str:
    """Fetch historical price data summary for a ticker."""
    try:
        market = MarketDataFetcher()
        data = market.get_historical_data(ticker, period=period)
        if data.empty:
            return json.dumps({"ticker": ticker, "error": "No historical data"})
        return json.dumps({
            "ticker": ticker,
            "period": period,
            "start": str(data.index.min()),
            "end": str(data.index.max()),
            "start_close": float(data["Close"].iloc[0]),
            "end_close": float(data["Close"].iloc[-1]),
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def summarize_sources_tool(ticker: str) -> str:
    """Fetch and summarize recent headlines for a ticker."""
    try:
        news = NewsAggregator()
        articles = news.fetch_news_for_keywords([ticker], days_back=7, max_results=5)
        summary = [
            {
                "title": article.get("title"),
                "source": article.get("source"),
                "url": article.get("url"),
            }
            for article in articles
        ]
        return json.dumps(summary, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def explain_signal_tool(signal_text: str) -> str:
    """Provide a short, plain-language explanation of a signal."""
    if not signal_text:
        return "No signal provided."
    return (
        "Signal explanation (plain language): "
        f"{signal_text.strip()[:360]}"
    )


@tool
def compare_two_stocks_tool(ticker_a: str, ticker_b: str) -> str:
    """Compare two tickers with headline and quote context."""
    try:
        market = MarketDataFetcher()
        quote_a = market.get_quote(ticker_a)
        quote_b = market.get_quote(ticker_b)
        return json.dumps({
            "ticker_a": quote_a,
            "ticker_b": quote_b,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# AGENT CREATORS
# =============================================================================

def create_scout_agent() -> Agent:
    """Create the Market Intelligence Scout agent."""
    return Agent(
        role="Market Intelligence Scout",
        goal="Gather breakthrough news, sentiment signals, and social media buzz for the target ticker.",
        backstory="""You are an expert signal detection specialist focused on exponential
technologies: AI, humanoid robotics, longevity biotech, and semiconductors. Your mission
is to scan news sources and surface only breakthrough moments—major product launches,
clinical trial results, regulatory approvals, partnership announcements, and technology
leaps. You filter noise ruthlessly and prioritize high-impact signals that could move
markets or indicate long-term paradigm shifts.""",
        tools=[finnhub_news_tool, finnhub_sentiment_tool, reddit_sentiment_tool],
        llm=_get_xai_llm(),
        verbose=True,
        allow_delegation=False
    )


def create_analyst_agent() -> Agent:
    """Create the Deep Alpha Investment Analyst agent."""
    return Agent(
        role="Deep Alpha Investment Analyst",
        goal="Analyze the impact of market signals and predict short-term price movements with conviction ratings.",
        backstory="""You are a sharp, optimistic-realistic investment analyst focused on
exponential technologies. You rate breakthrough impact on a scale of 1-10, predict
short-term price movements, flag key risks, and model long-term scenarios. You stay
grounded in evidence while thinking in decades. Your analysis style combines quantitative
rigor with qualitative insight about technology adoption curves and market dynamics.""",
        tools=[],
        llm=_get_xai_llm(),
        verbose=True,
        allow_delegation=False
    )


def create_forecaster_agent() -> Agent:
    """Create the Long-Term Scenarios Forecaster agent."""
    return Agent(
        role="Long-Term Scenarios Forecaster",
        goal="Generate personalized investment scenarios across Base, Bull, and Super-Bull cases.",
        backstory="""You are an expert at modeling exponential growth in breakthrough
technologies. You understand compound growth, technology adoption S-curves, and how
breakthrough events cascade into long-term value creation. You create Base (conservative),
Bull (optimistic), and Super-Bull (exponential breakthrough) scenarios that help investors
understand the range of possible outcomes over 5, 10, and 20 year timeframes.""",
        tools=[],
        llm=_get_xai_llm(),
        verbose=True,
        allow_delegation=False
    )


# =============================================================================
# TASK CREATORS
# =============================================================================

def create_scout_task(agent: Agent, ticker: str) -> Task:
    """Create the scouting task for gathering market intelligence."""
    return Task(
        description=f"""Gather comprehensive market intelligence for {ticker}:

1. Use the finnhub_news_tool to fetch recent news articles for {ticker}
2. Use the finnhub_sentiment_tool to get current sentiment and buzz data for {ticker}
3. Use the reddit_sentiment_tool to capture retail investor sentiment for {ticker}
4. Identify breakthrough signals: major announcements, technology leaps, regulatory changes
5. Filter out noise and focus on high-impact news items
6. Summarize the current market narrative and key themes

Focus on signals that could indicate paradigm shifts or significant price movements.""",
        expected_output="""A structured report containing:
- List of top 5 most impactful news items with brief summaries
- Current sentiment score and buzz metrics
- Reddit mentions and sentiment score
- Key themes and narratives in the market
- Any breakthrough signals identified
- Overall market mood (bullish/neutral/bearish) with reasoning

Format as a clear, structured report with sections.""",
        agent=agent
    )


def _build_memory_context(ticker: str) -> str:
    """Fetch similar past analyses for the ticker."""
    try:
        from memory.vector_store import VectorMemory  # type: ignore
        memory = VectorMemory()
        matches = memory.retrieve_similar_analyses(
            query_text=f"{ticker} investment analysis",
            top_k=3,
            ticker=ticker
        )
        if not matches:
            return ""

        lines = []
        for match in matches:
            metadata = match.get("metadata", {}) or {}
            timestamp = metadata.get("timestamp", "unknown")
            summary = (
                metadata.get("summary")
                or metadata.get("key_insight")
                or metadata.get("analysis_text", "")
            )
            summary = summary.replace("\n", " ").strip()
            if len(summary) > 220:
                summary = summary[:217].rstrip() + "..."
            lines.append(f"- {timestamp}: {summary}")

        return "\n\nSimilar past analyses:\n" + "\n".join(lines)
    except Exception:
        return ""


def create_analyst_task(agent: Agent, context: list, ticker: str) -> Task:
    """Create the analysis task for evaluating market signals."""
    memory_context = _build_memory_context(ticker)
    return Task(
        description="""Analyze the market intelligence gathered by the Scout and generate investment insights:

1. Review all news items and sentiment data from the Scout's report
2. Score each significant signal on impact (1-10 scale)
3. Determine overall sentiment and conviction level
4. Predict 30-day price outlook based on the signals
5. Identify key risks that could invalidate the thesis
6. Note any catalysts or upcoming events to watch

Be rigorous but decisive. Provide clear ratings and predictions.""" + memory_context,
        expected_output="""A structured analysis containing:
- Impact Score (1-10) with justification
- Sentiment: bullish/neutral/bearish with confidence level
- 30-Day Price Outlook: specific prediction with reasoning
- Key Insight: 1-2 sentence takeaway for investors
- Risks: 2-3 bullet points of potential downsides
- Catalysts: upcoming events that could move the stock

Format as a professional investment memo.""",
        agent=agent,
        context=context
    )


def create_forecast_task(agent: Agent, context: list) -> Task:
    """Create the forecasting task for long-term scenarios."""
    return Task(
        description="""Generate long-term investment scenarios based on the Analyst's assessment:

1. Review the impact score and key insights from the Analyst
2. Consider how current signals might compound over time
3. Model three scenarios for 5-year, 10-year, and 20-year timeframes:
   - BASE CASE: Conservative but realistic growth assumptions
   - BULL CASE: Strong technology adoption and execution
   - SUPER-BULL CASE: Exponential breakthrough scenarios
4. Identify key assumptions driving each scenario
5. Provide actionable insights for long-term investors

Think in decades while staying grounded in current evidence.""",
        expected_output="""A structured forecast containing:

For each timeframe (5yr, 10yr, 20yr):
- BASE CASE: Description and expected outcome
- BULL CASE: Description and expected outcome  
- SUPER-BULL CASE: Description and expected outcome

Key Assumptions:
- 3-4 bullet points on what must happen for each scenario

Investment Implications:
- Recommended position sizing and strategy
- Key milestones to watch

Format as a strategic planning document.""",
        agent=agent,
        context=context
    )


def create_chat_scout_task(agent: Agent, ticker: str, user_prompt: str) -> Task:
    """Create a scout task tailored for chat."""
    return Task(
        description=(
            f"Gather the most relevant signals for {ticker} to answer the user request:\n"
            f"{user_prompt}\n\n"
            "Use available tools to surface the most impactful headlines and sentiment."
        ),
        expected_output="A concise list of 3-5 relevant headlines and key market themes.",
        agent=agent,
    )


def create_chat_analyst_task(
    agent: Agent,
    context: list,
    ticker: str,
    user_prompt: str,
    risk_profile: str,
) -> Task:
    """Create an analyst task for chat responses."""
    return Task(
        description=(
            f"Answer the user's request for {ticker} with explainable, risk-framed analysis.\n"
            f"User request: {user_prompt}\n"
            f"Risk profile: {risk_profile}\n"
            "Include clear assumptions and confidence."
        ),
        expected_output="A structured response with TL;DR, why it matters, assumptions, confidence, and next steps.",
        agent=agent,
        context=context,
    )


def create_chat_forecast_task(
    agent: Agent,
    context: list,
    user_prompt: str,
    risk_profile: str,
) -> Task:
    """Create a forecast task for chat."""
    return Task(
        description=(
            "Generate a personalized forecast using the user's plan details.\n"
            f"User request: {user_prompt}\n"
            f"Risk profile: {risk_profile}\n"
            "Provide base/bull/super-bull scenarios with key assumptions."
        ),
        expected_output="A concise forecast summary with assumptions and risks.",
        agent=agent,
        context=context,
    )


# =============================================================================
# CREW CREATION
# =============================================================================

def create_analysis_crew(ticker: str) -> Crew:
    """
    Create the full analysis crew for a given ticker.
    
    Args:
        ticker: Stock ticker symbol to analyze
    
    Returns:
        Configured Crew ready to execute
    """
    scout = create_scout_agent()
    analyst = create_analyst_agent()
    forecaster = create_forecaster_agent()
    
    scout_task = create_scout_task(scout, ticker)
    analyst_task = create_analyst_task(analyst, context=[scout_task], ticker=ticker)
    forecast_task = create_forecast_task(forecaster, context=[analyst_task])
    
    return Crew(
        agents=[scout, analyst, forecaster],
        tasks=[scout_task, analyst_task, forecast_task],
        process=Process.sequential,
        verbose=True
    )


def create_chat_crew(context: Dict[str, Any]) -> Crew:
    """
    Create a chat-oriented crew based on user intent.

    Context keys:
    - intent
    - tickers
    - risk_profile
    - user_prompt
    """
    intent = context.get("intent", "general")
    tickers = context.get("tickers", [])
    ticker = tickers[0] if tickers else "NVDA"
    risk_profile = context.get("risk_profile", "medium")
    user_prompt = context.get("user_prompt", "")

    scout = create_scout_agent()
    analyst = create_analyst_agent()
    forecaster = create_forecaster_agent()

    if intent == "daily_brief":
        scout_task = create_chat_scout_task(scout, ticker, user_prompt)
        analyst_task = create_chat_analyst_task(
            analyst,
            context=[scout_task],
            ticker=ticker,
            user_prompt=user_prompt,
            risk_profile=risk_profile,
        )
        tasks = [scout_task, analyst_task]
        agents = [scout, analyst]
    elif intent == "forecast":
        forecast_task = create_chat_forecast_task(
            forecaster,
            context=[],
            user_prompt=user_prompt,
            risk_profile=risk_profile,
        )
        tasks = [forecast_task]
        agents = [forecaster]
    else:
        analyst_task = create_chat_analyst_task(
            analyst,
            context=[],
            ticker=ticker,
            user_prompt=user_prompt,
            risk_profile=risk_profile,
        )
        tasks = [analyst_task]
        agents = [analyst]

    return Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )


def run_analysis(ticker: str) -> str:
    """
    Run the full analysis pipeline for a ticker.
    
    Args:
        ticker: Stock ticker symbol to analyze
    
    Returns:
        Final crew output as string
    """
    crew = create_analysis_crew(ticker)
    result = crew.kickoff()
    output = str(result)

    try:
        from memory.vector_store import VectorMemory  # type: ignore
        memory = VectorMemory()
        memory.store_analysis(
            ticker=ticker,
            analysis_text=output,
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "ticker": ticker,
                "analysis_type": "crewai",
                "summary": output[:280]
            }
        )
    except Exception:
        pass

    return output


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    print(f"Running analysis for {ticker}...")
    output = run_analysis(ticker)
    print(output)
