"""
Unit Tests for IntentClassifier
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from intents import IntentClassifier


def test_daily_brief_intent():
    classifier = IntentClassifier()
    result = classifier.classify("What happened today?", known_tickers=["NVDA"])
    assert result.intent == "daily_brief"


def test_stock_question_intent_with_ticker():
    classifier = IntentClassifier()
    result = classifier.classify("Should I buy NVDA?", known_tickers=["NVDA"])
    assert result.intent == "stock_question"
    assert "NVDA" in result.tickers


def test_forecast_intent_with_contribution():
    classifier = IntentClassifier()
    result = classifier.classify("My plan is €300/month. What does the future look like?", known_tickers=[])
    assert result.intent == "forecast"
    assert result.monthly_contribution == 300.0


def test_explain_signal_intent():
    classifier = IntentClassifier()
    result = classifier.classify("Explain this signal like I'm new.", known_tickers=[])
    assert result.intent == "explain_signal"


def test_portfolio_summary_intent():
    classifier = IntentClassifier()
    result = classifier.classify("Show my portfolio positions.", known_tickers=[])
    assert result.intent == "portfolio_summary"
