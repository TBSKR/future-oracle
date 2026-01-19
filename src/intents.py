"""Intent detection and entity extraction for chat routing."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List, Optional


@dataclass
class IntentResult:
    intent: str
    tickers: List[str]
    timeframe: Optional[str]
    risk_profile: Optional[str]
    horizon: Optional[str]
    monthly_contribution: Optional[float]
    raw: str


class IntentClassifier:
    """Lightweight, rule-based intent classifier for chat messages."""

    _STOP_TOKENS = {
        "A", "AN", "AND", "ARE", "BUY", "FOR", "FROM", "HAS", "HOLD", "HOW",
        "I", "IN", "IS", "IT", "MY", "OF", "ON", "OR", "SELL", "SHOULD",
        "THE", "THIS", "TO", "TODAY", "WHAT", "WITH", "YOU", "YOUR",
    }

    _TIMEFRAME_MAP = {
        "1d": ["today", "1 day", "1d"],
        "1w": ["1 week", "1w", "7d", "week"],
        "1m": ["1 month", "1m", "30d", "month"],
        "3m": ["3 months", "3m", "quarter"],
        "6m": ["6 months", "6m", "half year"],
        "1y": ["1 year", "1y", "12 months", "year"],
    }

    def classify(self, message: str, known_tickers: Optional[List[str]] = None) -> IntentResult:
        text = message.strip()
        lowered = text.lower()

        tickers = self._extract_tickers(text, known_tickers)
        timeframe = self._extract_timeframe(lowered)
        risk_profile = self._extract_risk_profile(lowered)
        horizon = self._extract_horizon(lowered)
        monthly_contribution = self._extract_monthly_contribution(lowered)

        intent = self._infer_intent(lowered)

        return IntentResult(
            intent=intent,
            tickers=tickers,
            timeframe=timeframe,
            risk_profile=risk_profile,
            horizon=horizon,
            monthly_contribution=monthly_contribution,
            raw=text,
        )

    def _infer_intent(self, lowered: str) -> str:
        if re.search(r"\b(explain|eli5|like i'm new|break it down)\b", lowered):
            return "explain_signal"
        if re.search(r"\b(forecast|projection|future|what does the future|plan)\b", lowered):
            return "forecast"
        if re.search(r"\b(portfolio|holdings|positions|allocation)\b", lowered):
            return "portfolio_summary"
        if re.search(r"\b(daily brief|what happened|news today|market today)\b", lowered):
            return "daily_brief"
        if re.search(r"\b(should i buy|good buy|buy|sell|hold|is .* a good buy)\b", lowered):
            return "stock_question"
        return "general"

    def _extract_tickers(self, text: str, known_tickers: Optional[List[str]]) -> List[str]:
        candidates = set()
        known = {t.upper() for t in (known_tickers or [])}

        for match in re.findall(r"\$?[A-Za-z]{1,5}\b", text):
            token = match.replace("$", "").upper()
            if token in self._STOP_TOKENS:
                continue
            if known:
                if token in known:
                    candidates.add(token)
            else:
                if len(token) >= 2:
                    candidates.add(token)

        return sorted(candidates)

    def _extract_timeframe(self, lowered: str) -> Optional[str]:
        for timeframe, patterns in self._TIMEFRAME_MAP.items():
            if any(pat in lowered for pat in patterns):
                return timeframe
        return None

    def _extract_risk_profile(self, lowered: str) -> Optional[str]:
        if re.search(r"\b(low risk|conservative|cautious)\b", lowered):
            return "low"
        if re.search(r"\b(high risk|aggressive)\b", lowered):
            return "high"
        if re.search(r"\b(medium risk|balanced)\b", lowered):
            return "medium"
        return None

    def _extract_horizon(self, lowered: str) -> Optional[str]:
        if "short term" in lowered or "short-term" in lowered:
            return "short"
        if "medium term" in lowered or "medium-term" in lowered:
            return "medium"
        if "long term" in lowered or "long-term" in lowered:
            return "long"
        return None

    def _extract_monthly_contribution(self, lowered: str) -> Optional[float]:
        match = re.search(
            r"(?:€|\$)\s?([0-9]+(?:[.,][0-9]+)?)\s*(?:/|per)?\s*month",
            lowered,
        )
        if not match:
            return None
        value = match.group(1).replace(",", "")
        try:
            return float(value)
        except ValueError:
            return None
